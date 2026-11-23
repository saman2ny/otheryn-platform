export const ENABLED_PRODUCT = 'DentalPilot AI';

export const ENABLED_PRODUCTS = [ENABLED_PRODUCT] as const;

const ENABLED_SPECIALTIES = ['Dental'] as const;

export const isProductEnabled = (name: string) =>
  (ENABLED_PRODUCTS as readonly string[]).includes(name);

export const isIndustryEnabled = (name: string) =>
  (ENABLED_SPECIALTIES as readonly string[]).includes(name);

export const productAccessLabel = (name: string) => (isProductEnabled(name) ? 'Live' : 'Disabled');

export const industryAccessLabel = (name: string) =>
  isIndustryEnabled(name) ? 'Product Live' : 'Disabled';

export const isCrossSectorPlatformEnabled = () => false;