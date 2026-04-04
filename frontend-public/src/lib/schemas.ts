import { z } from 'zod';

export const emailSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
});

export type EmailFormValues = z.infer<typeof emailSchema>;
