import {
  FREE_EMAIL_DOMAINS,
  ISP_DOMAINS,
  isBlockedEmailDomain,
} from '@/lib/constants/free_domains';

describe('isBlockedEmailDomain', () => {
  it('blocks gmail.com (free email)', () => {
    expect(isBlockedEmailDomain('test@gmail.com')).toBe(true);
  });

  it('blocks rogers.com (ISP)', () => {
    expect(isBlockedEmailDomain('user@rogers.com')).toBe(true);
  });

  it('allows tdbank.ca (corporate)', () => {
    expect(isBlockedEmailDomain('ceo@tdbank.ca')).toBe(false);
  });

  it('allows utoronto.ca (university — not blocked)', () => {
    expect(isBlockedEmailDomain('prof@utoronto.ca')).toBe(false);
  });

  it('blocks yahoo.ca (free email)', () => {
    expect(isBlockedEmailDomain('user@yahoo.ca')).toBe(true);
  });

  it('blocks shaw.ca (ISP)', () => {
    expect(isBlockedEmailDomain('user@shaw.ca')).toBe(true);
  });

  it('is case-insensitive on domain', () => {
    expect(isBlockedEmailDomain('user@Gmail.COM')).toBe(true);
  });

  it('returns false for email without @ sign', () => {
    expect(isBlockedEmailDomain('notanemail')).toBe(false);
  });

  it('returns false for empty string', () => {
    expect(isBlockedEmailDomain('')).toBe(false);
  });
});

describe('domain sets', () => {
  it('FREE_EMAIL_DOMAINS contains expected entries', () => {
    expect(FREE_EMAIL_DOMAINS.has('gmail.com')).toBe(true);
    expect(FREE_EMAIL_DOMAINS.has('hotmail.com')).toBe(true);
    expect(FREE_EMAIL_DOMAINS.has('protonmail.com')).toBe(true);
  });

  it('ISP_DOMAINS contains expected entries', () => {
    expect(ISP_DOMAINS.has('shaw.ca')).toBe(true);
    expect(ISP_DOMAINS.has('bell.net')).toBe(true);
    expect(ISP_DOMAINS.has('telus.net')).toBe(true);
  });
});
