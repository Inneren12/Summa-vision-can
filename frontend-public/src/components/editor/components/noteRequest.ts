/**
 * Shared shape for any UI surface that wants to open the editor's single
 * NoteModal. Ownership of the modal instance lives in `index.tsx` so both
 * ReviewPanel and ReadOnlyBanner (and any future surface) route through
 * the same audit path: transitions carrying a note are never dispatched
 * directly — they always flow through NoteModal → onSubmit(note) → dispatch.
 */
export interface NoteRequestConfig {
  title: string;
  label: string;
  placeholder?: string;
  initialValue?: string;
  required: boolean;
  submitLabel: string;
  onSubmit: (note: string) => void;
}
