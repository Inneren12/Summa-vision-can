import {
  extractBackendErrorPayload,
  getBackendErrorI18nKey,
  KNOWN_BACKEND_ERROR_CODES,
  BACKEND_ERROR_I18N_KEYS,
} from '@/lib/api/errorCodes';

describe('extractBackendErrorPayload', () => {
  describe('nested envelope (publication contract)', () => {
    it('extracts code, message, details from nested 404 body', () => {
      const body = {
        detail: {
          error_code: 'PUBLICATION_NOT_FOUND',
          message: 'Publication not found.',
        },
      };
      expect(extractBackendErrorPayload(body)).toEqual({
        code: 'PUBLICATION_NOT_FOUND',
        message: 'Publication not found.',
        details: null,
        envelope: 'nested',
      });
    });

    it('extracts details when present (422 with validation_errors)', () => {
      const body = {
        detail: {
          error_code: 'PUBLICATION_UPDATE_PAYLOAD_INVALID',
          message: 'The submitted changes are invalid.',
          details: { validation_errors: [{ loc: ['body', 'headline'] }] },
        },
      };
      const payload = extractBackendErrorPayload(body);
      expect(payload.code).toBe('PUBLICATION_UPDATE_PAYLOAD_INVALID');
      expect(payload.details).toEqual({
        validation_errors: [{ loc: ['body', 'headline'] }],
      });
      expect(payload.envelope).toBe('nested');
    });
  });

  describe('flat envelope (auth middleware)', () => {
    it('extracts AUTH_API_KEY_MISSING with message from `error` field', () => {
      const body = { error: 'Missing X-API-KEY header', error_code: 'AUTH_API_KEY_MISSING' };
      expect(extractBackendErrorPayload(body)).toEqual({
        code: 'AUTH_API_KEY_MISSING',
        message: 'Missing X-API-KEY header',
        details: null,
        envelope: 'flat',
      });
    });

    it('extracts AUTH_ADMIN_RATE_LIMITED 429', () => {
      const body = { error: 'Rate limited', error_code: 'AUTH_ADMIN_RATE_LIMITED' };
      expect(extractBackendErrorPayload(body).code).toBe('AUTH_ADMIN_RATE_LIMITED');
    });
  });

  describe('precedence: nested wins when both present', () => {
    it('returns nested code when both nested and flat are populated', () => {
      const body = {
        detail: { error_code: 'PUBLICATION_NOT_FOUND', message: 'nested' },
        error_code: 'AUTH_API_KEY_INVALID',
      };
      const payload = extractBackendErrorPayload(body);
      expect(payload.code).toBe('PUBLICATION_NOT_FOUND');
      expect(payload.envelope).toBe('nested');
    });
  });

  describe('edge cases (must not throw)', () => {
    it('returns empty payload for null body', () => {
      expect(extractBackendErrorPayload(null).envelope).toBe('none');
    });

    it('returns empty payload for undefined body', () => {
      expect(extractBackendErrorPayload(undefined).envelope).toBe('none');
    });

    it('returns empty payload for string body', () => {
      expect(extractBackendErrorPayload('error').envelope).toBe('none');
    });

    it('returns empty payload when detail is a string (legacy 422 fallback)', () => {
      expect(extractBackendErrorPayload({ detail: 'Bad request' }).envelope).toBe('none');
    });

    it('returns empty payload when detail is an array (legacy validation list)', () => {
      expect(
        extractBackendErrorPayload({ detail: [{ loc: ['x'], msg: 'bad' }] }).envelope,
      ).toBe('none');
    });

    it('returns empty payload when error_code is non-string', () => {
      expect(
        extractBackendErrorPayload({ detail: { error_code: 42 } }).envelope,
      ).toBe('none');
    });
  });

  describe('unknown codes preserved', () => {
    it('returns raw string for unknown codes (caller responsibility to warn)', () => {
      const body = { detail: { error_code: 'TOTALLY_NEW_CODE', message: 'x' } };
      const payload = extractBackendErrorPayload(body);
      expect(payload.code).toBe('TOTALLY_NEW_CODE');
      expect(payload.envelope).toBe('nested');
    });
  });
});

describe('getBackendErrorI18nKey', () => {
  it('returns null for null code', () => {
    expect(getBackendErrorI18nKey(null)).toBeNull();
  });

  it('returns null for unknown code', () => {
    expect(getBackendErrorI18nKey('TOTALLY_NEW_CODE')).toBeNull();
  });

  it.each(KNOWN_BACKEND_ERROR_CODES)('returns the mapped key for %s', (code) => {
    expect(getBackendErrorI18nKey(code)).toBe(BACKEND_ERROR_I18N_KEYS[code]);
  });
});

describe('Phase 3.1d resolver error codes', () => {
  it('maps MAPPING_NOT_FOUND to binding.resolve.mapping_not_found', () => {
    expect(getBackendErrorI18nKey('MAPPING_NOT_FOUND')).toBe(
      'publication.binding.resolve.mapping_not_found',
    );
  });

  it('maps RESOLVE_INVALID_FILTERS to binding.resolve.invalid_filters', () => {
    expect(getBackendErrorI18nKey('RESOLVE_INVALID_FILTERS')).toBe(
      'publication.binding.resolve.invalid_filters',
    );
  });

  it('maps RESOLVE_CACHE_MISS to binding.resolve.cache_miss', () => {
    expect(getBackendErrorI18nKey('RESOLVE_CACHE_MISS')).toBe(
      'publication.binding.resolve.cache_miss',
    );
  });
});

describe('nested envelope (auth middleware, DEBT-034)', () => {
  it('extracts auth.missing_api_key from nested envelope', () => {
    const body = {
      detail: {
        error_code: 'auth.missing_api_key',
        message: 'Missing X-API-KEY header',
        context: {},
      },
    };
    const payload = extractBackendErrorPayload(body);
    expect(payload.code).toBe('auth.missing_api_key');
    expect(payload.envelope).toBe('nested');
  });

  it('maps auth.missing_api_key to existing snake_case i18n key', () => {
    expect(getBackendErrorI18nKey('auth.missing_api_key')).toBe(
      'errors.backend.auth_api_key_missing',
    );
  });

  it('maps all four auth wire codes via dictionary', () => {
    expect(getBackendErrorI18nKey('auth.not_configured')).toBe(
      'errors.backend.auth_not_configured',
    );
    expect(getBackendErrorI18nKey('auth.invalid_api_key')).toBe(
      'errors.backend.auth_api_key_invalid',
    );
    expect(getBackendErrorI18nKey('auth.admin_rate_limited')).toBe(
      'errors.backend.auth_admin_rate_limited',
    );
  });
});
