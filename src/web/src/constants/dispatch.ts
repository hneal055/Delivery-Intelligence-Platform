export const JOB_TYPES = [
  { value: 'delivery', label: 'Delivery' },
  { value: 'pickup', label: 'Pickup' },
  { value: 'service', label: 'Service' },
  { value: 'exception', label: 'Exception' },
] as const;

export type JobType = (typeof JOB_TYPES)[number]['value'];
