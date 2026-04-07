import { requireNativeModule } from 'expo-modules-core';

const ExpoCameraLens = requireNativeModule('ExpoCameraLens');

export type LensType = 'ultra-wide' | 'wide' | 'telephoto';

/**
 * Switch the active camera capture session to a different lens.
 * Works by swapping the AVCaptureDeviceInput on the running AVCaptureSession
 * that WebRTC/LiveKit created — does NOT touch audio.
 */
export async function switchLens(type: LensType): Promise<boolean> {
  return ExpoCameraLens.switchLens(type);
}

/**
 * Get available back camera lenses on this device.
 * Returns array like ['ultra-wide', 'wide', 'telephoto'].
 */
export async function getAvailableLenses(): Promise<LensType[]> {
  return ExpoCameraLens.getAvailableLenses();
}
