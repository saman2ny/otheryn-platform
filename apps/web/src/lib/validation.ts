import { z } from 'zod';

export const bookingSpecialties = [
  'Dental',
  'Fertility & IVF',
  'Dermatology',
  'Ophthalmology',
  'Cardiology',
  'Orthopaedics',
  'Other',
] as const;

export const bookingProviderOptions = [
  '1 provider',
  '2–5 providers',
  '6–10 providers',
  '11–20 providers',
  '21–50 providers',
  'More than 50 providers',
] as const;

export const bookingTimeSlots = ['09:00', '10:30', '13:00', '14:30', '16:00'] as const;

export const today = new Date().toISOString().slice(0, 10);

const isDateInPast = (value: string) => value < today;

const isExpiryInFuture = (value: string) => {
  const match = value.match(/^(\d{2})\/(\d{2})$/);
  if (!match) return false;

  const month = Number(match[1]);
  const year = 2000 + Number(match[2]);
  const now = new Date();

  return year > now.getFullYear() || (year === now.getFullYear() && month >= now.getMonth() + 1);
};

const passesLuhn = (value: string) => {
  const digits = value.replace(/\s+/g, '');
  if (!/^\d{15,16}$/.test(digits)) return false;

  let sum = 0;
  let shouldDouble = false;

  for (let index = digits.length - 1; index >= 0; index -= 1) {
    let digit = Number(digits[index]);

    if (shouldDouble) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }

    sum += digit;
    shouldDouble = !shouldDouble;
  }

  return sum % 10 === 0;
};

export const bookingSchema = z.object({
  firstName: z
    .string()
    .trim()
    .min(1, 'Enter your first name.')
    .max(80, 'First name is too long.'),
  lastName: z
    .string()
    .trim()
    .min(1, 'Enter your last name.')
    .max(80, 'Last name is too long.'),
  email: z
    .string()
    .trim()
    .min(1, 'Enter your work email.')
    .email('Enter a valid email address.')
    .max(254, 'Email is too long.'),
  practice: z
    .string()
    .trim()
    .min(1, 'Enter your practice name.')
    .max(160, 'Practice name is too long.'),
  specialty: z.enum(['Dental'], {
    message: 'Currently, walkthrough bookings are available for dental practices only.',
  }),
  providers: z.enum(bookingProviderOptions, {
    message: 'Select the number of providers.',
  }),
  date: z
    .string()
    .trim()
    .min(1, 'Choose a date.')
    .refine((value) => !isDateInPast(value), 'Choose a date from today onward.'),
  time: z.enum(bookingTimeSlots, { message: 'Choose an available time.' }),
});

export const contactSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Enter your name.')
    .max(120, 'Name is too long.'),
  email: z
    .string()
    .trim()
    .min(1, 'Enter your email.')
    .email('Enter a valid email address.')
    .max(254, 'Email is too long.'),
  practice: z
    .string()
    .trim()
    .min(1, 'Enter your practice name.')
    .max(160, 'Practice name is too long.'),
  message: z
    .string()
    .trim()
    .min(10, 'Tell us a little more (at least 10 characters).')
    .max(2000, 'Message is too long.'),
});

export const checkoutSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, 'Enter your work email.')
    .email('Enter a valid work email.')
    .max(254, 'Email is too long.'),
  cardName: z
    .string()
    .trim()
    .min(1, 'Enter the cardholder name.')
    .max(120, 'Cardholder name is too long.'),
  cardNumber: z
    .string()
    .trim()
    .refine(passesLuhn, 'Enter a valid card number.'),
  expiry: z
    .string()
    .trim()
    .regex(/^(0[1-9]|1[0-2])\/\d{2}$/, 'Use MM/YY.')
    .refine(isExpiryInFuture, 'Card has expired.'),
  cvc: z
    .string()
    .trim()
    .regex(/^\d{3,4}$/, 'Enter a valid CVC.'),
});

export type BookingInput = z.infer<typeof bookingSchema>;
export type ContactInput = z.infer<typeof contactSchema>;
export type CheckoutInput = z.infer<typeof checkoutSchema>;

export const getFieldErrors = (error: z.ZodError): Record<string, string> => {
  const fieldErrors: Record<string, string> = {};

  for (const issue of error.issues) {
    const field = issue.path[0];
    if (typeof field === 'string' && !fieldErrors[field]) {
      fieldErrors[field] = issue.message;
    }
  }

  return fieldErrors;
};