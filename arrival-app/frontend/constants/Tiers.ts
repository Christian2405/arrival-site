/**
 * Subscription tier limits — gates features based on plan.
 * Matches the website's Pro/Business feature set.
 */

export interface TierLimits {
  maxQueries: number; // -1 = unlimited
  maxDocs: number;    // -1 = unlimited
  jobMode: boolean;
  proactiveAlerts: boolean;
  teamDocs: boolean;
  voiceOutput: boolean;
}

export const TIER_LIMITS: Record<string, TierLimits> = {
  free: {
    maxQueries: 10,
    maxDocs: 0,
    jobMode: false,
    proactiveAlerts: false,
    teamDocs: false,
    voiceOutput: false,
  },
  pro: {
    maxQueries: 50,
    maxDocs: 20,
    jobMode: false,
    proactiveAlerts: false,
    teamDocs: false,
    voiceOutput: true,
  },
  business: {
    maxQueries: -1,
    maxDocs: -1,
    jobMode: true,
    proactiveAlerts: true,
    teamDocs: true,
    voiceOutput: true,
  },
  enterprise: {
    maxQueries: -1,
    maxDocs: -1,
    jobMode: true,
    proactiveAlerts: true,
    teamDocs: true,
    voiceOutput: true,
  },
};

export function getTierLimits(plan: string): TierLimits {
  return TIER_LIMITS[plan] || TIER_LIMITS.free;
}
