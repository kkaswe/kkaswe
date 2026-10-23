/**
 * Foreground-only automatic daily KuGou benefit flow:
 * 1. claim daily listening VIP; 2. upgrade to daily Concept VIP.
 * Both steps are independently persisted per account/day. No background daemon.
 */
import * as SecureStore from 'expo-secure-store';

import { showToast } from '@/components/ui/toast';
import { isLoggedIn } from '@/features/account/user-api';
import {
  getVipSignInDayKey,
  signInDailyVip,
  upgradeDailyVip,
} from '@/features/account/vip-api';
import { isAutoDailySignInEnabled } from '@/features/settings/store';
import { bootstrapMobileApi, getApiSession } from '@/lib/kugou-api';

const STORAGE_PREFIX = 'moekoe.autoDailyVip.v1.';
const RETRY_COOLDOWN_MS = 60 * 60 * 1000;

type DayState = {
  date: string;
  claimed: boolean;
  upgraded: boolean;
  blocked: boolean;
};

const stateCache = new Map<string, DayState>();
const lastAttempts = new Map<string, number>();
let running: Promise<void> | null = null;
let rerunRequested = false;

function freshState(date: string): DayState {
  return { date, claimed: false, upgraded: false, blocked: false };
}

async function loadState(userId: string, date: string): Promise<DayState> {
  const cacheKey = `${userId}:${date}`;
  const cached = stateCache.get(cacheKey);
  if (cached) return cached;

  let state = freshState(date);
  try {
    const raw = await SecureStore.getItemAsync(`${STORAGE_PREFIX}${userId}`);
    if (raw) {
      const parsed: unknown = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') {
        const saved = parsed as Partial<DayState>;
        if (saved.date === date) {
          state = {
            date,
            claimed: saved.claimed === true,
            upgraded: saved.upgraded === true,
            blocked: saved.blocked === true,
          };
        }
      }
    }
  } catch {
    // SecureStore may be unavailable; the session still uses the memory cache.
  }
  stateCache.set(cacheKey, state);
  return state;
}

async function persistState(userId: string, state: DayState): Promise<void> {
  stateCache.set(`${userId}:${state.date}`, state);
  try {
    await SecureStore.setItemAsync(`${STORAGE_PREFIX}${userId}`, JSON.stringify(state));
  } catch {
    console.warn('[auto-daily-vip] Failed to persist current progress.');
  }
}

function mayAttempt(userId: string, date: string, step: 'claim' | 'upgrade'): boolean {
  const key = `${userId}:${date}:${step}`;
  const now = Date.now();
  if (now - (lastAttempts.get(key) ?? 0) < RETRY_COOLDOWN_MS) return false;
  lastAttempts.set(key, now);
  return true;
}

function sameAccount(userId: string): boolean {
  return isLoggedIn() && getApiSession().userid === userId;
}

async function performAutoDailyVip(): Promise<void> {
  // Can be invoked after a login flow, even when the user disabled the setting.
  if (!isAutoDailySignInEnabled()) return;

  try {
    await bootstrapMobileApi();
    if (!isLoggedIn()) return;
    const userId = getApiSession().userid;
    if (!userId || !/^\d+$/.test(userId)) return;

    const date = getVipSignInDayKey();
    const state = await loadState(userId, date);
    if (state.blocked || state.upgraded) return;
    if (!sameAccount(userId) || !isAutoDailySignInEnabled()) return;

    let claimedThisRun = false;
    if (!state.claimed) {
      if (!mayAttempt(userId, date, 'claim')) return;
      const result = await signInDailyVip();
      if (!sameAccount(userId) || !isAutoDailySignInEnabled()) return;

      if (result.blocked) {
        state.blocked = true;
        await persistState(userId, state);
        showToast('酷狗账号触发风控，已暂停今日自动领取');
        return;
      }
      if (!result.canUpgrade) {
        console.warn('[auto-daily-vip] Claim not confirmed:', result.message);
        return; // Never upgrade unless daily claim was confirmed.
      }

      state.claimed = true;
      claimedThisRun = !result.alreadyDone;
      await persistState(userId, state); // Preserve claim if upgrade fails.
    }

    if (!sameAccount(userId) || !isAutoDailySignInEnabled()) return;
    if (state.upgraded || !mayAttempt(userId, date, 'upgrade')) return;

    const upgrade = await upgradeDailyVip();
    if (!sameAccount(userId)) return;
    if (upgrade.confirmedDone) {
      state.upgraded = true;
      await persistState(userId, state);
      showToast(upgrade.alreadyDone ? '今日畅听及概念版 VIP 权益已领取' : '自动签到并升级概念版 VIP 成功');
    } else if (upgrade.blocked) {
      state.blocked = true;
      await persistState(userId, state);
      showToast('已完成签到，升级触发风控，今日暂停自动尝试');
    } else {
      console.warn('[auto-daily-vip] Upgrade not confirmed:', upgrade.message);
      if (claimedThisRun) showToast('自动签到成功；概念版 VIP 升级暂未完成');
    }
  } catch (error) {
    // Automatic requests must not prevent the app from launching or playing audio.
    console.warn('[auto-daily-vip] Failed:', error);
  }
}

/** Collapses simultaneous triggers and performs one follow-up if login completes mid-run. */
export function runAutoDailySignIn(): Promise<void> {
  if (running) {
    rerunRequested = true;
    return running;
  }

  const task = (async () => {
    do {
      rerunRequested = false;
      await performAutoDailyVip();
    } while (rerunRequested);
  })();

  running = task;
  void task.finally(() => {
    if (running === task) running = null;
  });
  return task;
}
