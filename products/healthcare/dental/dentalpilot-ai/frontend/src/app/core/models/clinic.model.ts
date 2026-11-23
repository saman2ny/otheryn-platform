export type ClinicSpecialty =
  'general-dentistry' | 'orthodontics' | 'cosmetic-dentistry' | 'implants' | 'pediatric-dentistry';

export interface ClinicProfile {
  id: string;
  name: string;
  specialty: ClinicSpecialty;
  aboutText: string;
  website?: string;
  phone: string;
  address: string;
  city: string;
  country: string;
  logoUrl?: string;
  brandTone: 'friendly' | 'professional' | 'premium' | 'playful';
  targetAudience: string;
}

export type UpdateClinicProfileRequest = Omit<ClinicProfile, 'id'>;
