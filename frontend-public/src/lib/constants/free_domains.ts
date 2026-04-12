export const FREE_EMAIL_DOMAINS = new Set([
  "gmail.com",
  "yahoo.com",
  "yahoo.ca",
  "outlook.com",
  "hotmail.com",
  "hotmail.ca",
  "protonmail.com",
  "protonmail.ch",
  "icloud.com",
  "mail.com",
  "aol.com",
  "zoho.com",
  "yandex.com",
  "gmx.com",
  "live.com",
  "live.ca",
  "msn.com",
]);

export const ISP_DOMAINS = new Set([
  "shaw.ca",
  "rogers.com",
  "bell.net",
  "bell.ca",
  "telus.net",
  "videotron.ca",
  "sasktel.net",
  "eastlink.ca",
  "cogeco.ca",
  "tbaytel.net",
  "northwestel.net",
  "mts.net",
  "sympatico.ca",
]);

// Only block FREE email domains on the form — ISP emails are accepted
// (backend scores ISP as low-priority but does not reject them)
export function isBlockedEmailDomain(email: string): boolean {
  const domain = email.split("@")[1]?.toLowerCase();
  if (!domain) return false;
  return FREE_EMAIL_DOMAINS.has(domain);
}
