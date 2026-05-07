/**
 * Phase 3.1d Slice 4a — usePublishAction tests.
 */
import React from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { usePublishAction } from '../usePublishAction';
import type { WalkerResult } from '../../utils/walker';

jest.mock('@/lib/api/admin', () => {
  class AdminPublicationNotFoundError extends Error {
    constructor(id: string) {
      super(`Publication ${id} not found`);
      this.name = 'AdminPublicationNotFoundError';
    }
  }
  return {
    publishAdminPublication: jest.fn(),
    AdminPublicationNotFoundError,
  };
});

import {
  publishAdminPublication,
  AdminPublicationNotFoundError,
} from '@/lib/api/admin';

const publishMock = publishAdminPublication as jest.MockedFunction<
  typeof publishAdminPublication
>;

const emptyWalker: WalkerResult = {
  boundBlocks: [],
  deferred: [],
  skipped: [],
};

const oneBlockWalker: WalkerResult = {
  boundBlocks: [
    {
      block_id: 'b1',
      cube_id: 'c1',
      semantic_key: 's1',
      dims: [1],
      members: [12],
      period: '2024-Q3',
    },
  ],
  deferred: [],
  skipped: [],
};

beforeEach(() => {
  publishMock.mockReset();
});

describe('usePublishAction — modal lifecycle', () => {
  it('initiate opens modal when publicationId present', () => {
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: 'p1',
        onPublishSuccess: jest.fn(),
        onNotFound: jest.fn(),
      }),
    );
    expect(result.current.isModalOpen).toBe(false);
    act(() => result.current.initiate());
    expect(result.current.isModalOpen).toBe(true);
  });

  it('initiate no-ops when publicationId null and warns', () => {
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: null,
        onPublishSuccess: jest.fn(),
        onNotFound: jest.fn(),
      }),
    );
    act(() => result.current.initiate());
    expect(result.current.isModalOpen).toBe(false);
    expect(warnSpy).toHaveBeenCalledTimes(1);
    warnSpy.mockRestore();
  });

  it('cancel closes modal', () => {
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: 'p1',
        onPublishSuccess: jest.fn(),
        onNotFound: jest.fn(),
      }),
    );
    act(() => result.current.initiate());
    expect(result.current.isModalOpen).toBe(true);
    act(() => result.current.cancel());
    expect(result.current.isModalOpen).toBe(false);
  });
});

describe('usePublishAction — confirm flow', () => {
  it('calls publishAdminPublication with bound_blocks from walker', async () => {
    publishMock.mockResolvedValueOnce({
      etag: 'etag-1',
      document: {} as never,
    });
    const onSuccess = jest.fn();
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: 'p1',
        onPublishSuccess: onSuccess,
        onNotFound: jest.fn(),
      }),
    );
    act(() => result.current.initiate());
    await act(async () => {
      await result.current.confirm(oneBlockWalker);
    });
    expect(publishMock).toHaveBeenCalledTimes(1);
    expect(publishMock).toHaveBeenCalledWith('p1', {
      bound_blocks: oneBlockWalker.boundBlocks,
    });
  });

  it('dispatches onPublishSuccess + closes modal on success', async () => {
    publishMock.mockResolvedValueOnce({
      etag: 'etag-1',
      document: {} as never,
    });
    const onSuccess = jest.fn();
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: 'p1',
        onPublishSuccess: onSuccess,
        onNotFound: jest.fn(),
      }),
    );
    act(() => result.current.initiate());
    await act(async () => {
      await result.current.confirm(emptyWalker);
    });
    expect(onSuccess).toHaveBeenCalledTimes(1);
    expect(result.current.isModalOpen).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('on 404 calls onNotFound + closes modal + does not call onPublishSuccess', async () => {
    publishMock.mockRejectedValueOnce(new AdminPublicationNotFoundError('p1'));
    const onSuccess = jest.fn();
    const onNotFound = jest.fn();
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: 'p1',
        onPublishSuccess: onSuccess,
        onNotFound,
      }),
    );
    act(() => result.current.initiate());
    await act(async () => {
      await result.current.confirm(emptyWalker);
    });
    expect(onNotFound).toHaveBeenCalledTimes(1);
    expect(onSuccess).not.toHaveBeenCalled();
    expect(result.current.isModalOpen).toBe(false);
  });

  it('on generic error sets error state + leaves modal open', async () => {
    publishMock.mockRejectedValueOnce(new Error('Server boom'));
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: 'p1',
        onPublishSuccess: jest.fn(),
        onNotFound: jest.fn(),
      }),
    );
    act(() => result.current.initiate());
    await act(async () => {
      await result.current.confirm(emptyWalker);
    });
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('Server boom');
    expect(result.current.isModalOpen).toBe(true);
  });

  it('blocks double-confirm while a publish is in flight', async () => {
    let resolvePublish: () => void = () => {};
    publishMock.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolvePublish = () =>
            resolve({ etag: null, document: {} as never });
        }),
    );
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: 'p1',
        onPublishSuccess: jest.fn(),
        onNotFound: jest.fn(),
      }),
    );
    act(() => result.current.initiate());
    let firstPromise!: Promise<void>;
    act(() => {
      firstPromise = result.current.confirm(emptyWalker);
    });
    await waitFor(() => expect(result.current.isPublishing).toBe(true));
    // Second call while first in flight should be a no-op
    await act(async () => {
      await result.current.confirm(emptyWalker);
    });
    expect(publishMock).toHaveBeenCalledTimes(1);
    await act(async () => {
      resolvePublish();
      await firstPromise;
    });
  });

  it('isPublishing flag transitions true → false', async () => {
    publishMock.mockResolvedValueOnce({
      etag: null,
      document: {} as never,
    });
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: 'p1',
        onPublishSuccess: jest.fn(),
        onNotFound: jest.fn(),
      }),
    );
    expect(result.current.isPublishing).toBe(false);
    act(() => result.current.initiate());
    await act(async () => {
      await result.current.confirm(emptyWalker);
    });
    expect(result.current.isPublishing).toBe(false);
  });

  it('error cleared when initiate is called again', async () => {
    publishMock.mockRejectedValueOnce(new Error('boom'));
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: 'p1',
        onPublishSuccess: jest.fn(),
        onNotFound: jest.fn(),
      }),
    );
    act(() => result.current.initiate());
    await act(async () => {
      await result.current.confirm(emptyWalker);
    });
    expect(result.current.error?.message).toBe('boom');
    act(() => result.current.initiate());
    expect(result.current.error).toBeNull();
  });

  it('cancel blocked while isPublishing=true', async () => {
    let resolvePublish: () => void = () => {};
    publishMock.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolvePublish = () =>
            resolve({ etag: null, document: {} as never });
        }),
    );
    const { result } = renderHook(() =>
      usePublishAction({
        publicationId: 'p1',
        onPublishSuccess: jest.fn(),
        onNotFound: jest.fn(),
      }),
    );
    act(() => result.current.initiate());
    let inflight!: Promise<void>;
    act(() => {
      inflight = result.current.confirm(emptyWalker);
    });
    await waitFor(() => expect(result.current.isPublishing).toBe(true));
    act(() => result.current.cancel());
    expect(result.current.isModalOpen).toBe(true);
    await act(async () => {
      resolvePublish();
      await inflight;
    });
  });
});
