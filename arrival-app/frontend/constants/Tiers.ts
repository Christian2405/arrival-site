/**
 * Subscription tier limits — gates features based on plan.
 * Matches the website's Pro/Business feature set.
 */

export interface TierLimits {
  maxDocs: number;
  jobMode: boolean;
  proactiveAlerts: boolean;
  teamDocs: boolean;
  voiceOutput: boolean;
}

export const TIER_LIMITS: Record<string, TierLimits> = {
  free: {
    maxDocs: 10,
    jobMode: false,
    proactiveAlerts: false,
    teamDocs: false,
    voiceOutput: true,
  },
  pro: {
    maxDocs: 50,
    jobMode: false,
    proactiveAlerts: false,
    teamDocs: false,
    voiceOutput: true,
  },
  business: {
    maxDocs: 999,
    jobMode: true,
    proactiveAlerts: true,
    teamDocs: true,
    voiceOutput: true,
  },
};

export function getTierLimits(plan: string): TierLimits {
  return TIER_LIMITS[plan] || TIER_LIMITS.free;
}
