#!/usr/bin/env python3
"""Apply MoeKoe Music Mobile automatic daily VIP claim & upgrade changes to v1.1.0/master.

Usage: python apply_auto_daily_vip.py /path/to/MoeKoeMusic-Mobile
Fail-closed: checks all anchors and writes nothing until validation succeeds.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import sys
from datetime import datetime


def change(source: str, old: str, new: str, name: str) -> str:
    if new in source:
        return source  # idempotent; replacement may intentionally contain old anchor
    count = source.count(old)
    if count == 1:
        return source.replace(old, new)
    raise ValueError(f"{name}: expected one exact patch anchor; found {count}. "
                     "Upstream may have changed. No files have been written.")


def plan(root: Path, patch_root: Path):
    files = [
        'src/features/account/vip-api.ts',
        'src/features/settings/storage.ts',
        'src/features/settings/store.ts',
        'src/app/_layout.tsx',
        'src/app/login.tsx',
        'src/app/settings.tsx',
    ]
    missing = [p for p in files if not (root / p).is_file()]
    if missing:
        raise ValueError('Missing files in repository:\n' + '\n'.join(missing))
    content = {p: (root / p).read_text(encoding='utf-8') for p in files}

    p = 'src/features/account/vip-api.ts'
    s = content[p]
    s = change(s,
        "function todayKey(): string {\n  return new Date().toISOString().split('T')[0];\n}\n",
        "// KuGou daily benefits reset on the mainland-China calendar day (UTC+08:00).\n"
        "export function getVipSignInDayKey(): string {\n"
        "  return new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString().slice(0, 10);\n}\n",
        p)
    s = change(s,
        'mobileApi.youth_day_vip({ receive_day: todayKey() })',
        'mobileApi.youth_day_vip({ receive_day: getVipSignInDayKey() })', p)
    s = change(s,
        '  canUpgrade?: boolean;\n',
        '  canUpgrade?: boolean;\n'
        '  /** Upgrade result is definitively successful or server says already upgraded. */\n'
        '  confirmedDone?: boolean;\n'
        '  /** Server risk control: stop automatic attempts for this account/day. */\n'
        '  blocked?: boolean;\n', p)
    s = change(s,
        "return { message: '当前账号存在风控，请前往手机酷狗领取', alreadyDone: true };",
        "return { message: '当前账号存在风控，请前往手机酷狗领取', alreadyDone: true, blocked: true };", p)
    s = change(s,
        "return { message: '升级成功，获得 1 天概念版 VIP', alreadyDone: false };",
        "return { message: '升级成功，获得 1 天概念版 VIP', alreadyDone: false, confirmedDone: true };", p)
    # Scope this replacement to the upgrade function: catch code 131001 appears twice.
    start = s.index('export async function upgradeDailyVip()')
    head, tail = s[:start], s[start:]
    tail = change(tail,
        "return { message: '你今天已经签到过了', alreadyDone: true };",
        "return { message: '你今天已经签到过了', alreadyDone: true, confirmedDone: true };", p)
    tail = change(tail,
        "return { message: '当前账号风控,请前往手机端领取', alreadyDone: true };",
        "return { message: '当前账号风控,请前往手机端领取', alreadyDone: true, blocked: true };", p)
    s = head + tail
    content[p] = s

    p = 'src/features/settings/storage.ts'
    s = content[p]
    s = change(s,
        '  accentId?: unknown;\n',
        '  accentId?: unknown;\n  autoDailySignIn?: unknown;\n', p)
    s = change(s,
        '  accentId: string;\n',
        '  accentId: string;\n  autoDailySignIn: boolean;\n', p)
    content[p] = s

    p = 'src/features/settings/store.ts'
    s = content[p]
    s = change(s,
        '  accentId: AccentPresetId;\n',
        '  accentId: AccentPresetId;\n  autoDailySignIn: boolean;\n', p)
    s = change(s,
        '  accentId: DEFAULT_ACCENT_ID,\n',
        '  accentId: DEFAULT_ACCENT_ID,\n  autoDailySignIn: true,\n', p)
    s = change(s,
        "        accentId: stored && isAccentPresetId(stored.accentId) ? stored.accentId : DEFAULT_ACCENT_ID,\n",
        "        accentId: stored && isAccentPresetId(stored.accentId) ? stored.accentId : DEFAULT_ACCENT_ID,\n"
        "        autoDailySignIn: stored?.autoDailySignIn !== false,\n", p)
    s = change(s,
        '  const { themeMode, accentId } = settingsStore.getState();\n'
        '  void writeStoredAppearance({ themeMode, accentId });\n',
        '  const { themeMode, accentId, autoDailySignIn } = settingsStore.getState();\n'
        '  void writeStoredAppearance({ themeMode, accentId, autoDailySignIn });\n', p)
    s = change(s,
        '  setAccentId(accentId: AccentPresetId) {\n'
        '    settingsStore.setState({ accentId });\n'
        '    persist();\n'
        '  },\n',
        '  setAccentId(accentId: AccentPresetId) {\n'
        '    settingsStore.setState({ accentId });\n'
        '    persist();\n'
        '  },\n'
        '  setAutoDailySignIn(autoDailySignIn: boolean) {\n'
        '    settingsStore.setState({ autoDailySignIn });\n'
        '    persist();\n'
        '  },\n', p)
    s = change(s,
        'export function useSettings(): SettingsState {\n',
        'export function isAutoDailySignInEnabled(): boolean {\n'
        '  const current = settingsStore.getState();\n'
        '  return current.hydrated && current.autoDailySignIn;\n'
        '}\n\n'
        'export function useSettings(): SettingsState {\n', p)
    content[p] = s

    p = 'src/app/_layout.tsx'
    s = content[p]
    s = change(s,
        "import { useEffect, useMemo } from 'react';\n",
        "import { useEffect, useMemo } from 'react';\n"
        "import { AppState } from 'react-native';\n", p)
    s = change(s,
        "import { hydrateSettings, useSettingsHydrated } from '@/features/settings/store';\n",
        "import { hydrateSettings, useSettings } from '@/features/settings/store';\n"
        "import { runAutoDailySignIn } from '@/features/account/auto-sign-in';\n", p)
    s = change(s,
        '  const hydrated = useSettingsHydrated();\n',
        '  const { hydrated, autoDailySignIn } = useSettings();\n', p)
    anchor = "  if (!hydrated) {\n    // 原生 splash 覆盖期间完成偏好读取,首帧即正确主题。\n"
    insert = (
        "  useEffect(() => {\n"
        "    if (!hydrated || !autoDailySignIn) return;\n"
        "    // Run at launch and whenever the application returns to the foreground.\n"
        "    void runAutoDailySignIn();\n"
        "    const subscription = AppState.addEventListener('change', (state) => {\n"
        "      if (state === 'active') void runAutoDailySignIn();\n"
        "    });\n"
        "    return () => subscription.remove();\n"
        "  }, [hydrated, autoDailySignIn]);\n\n"
    )
    s = change(s, anchor, insert + anchor, p)
    content[p] = s

    p = 'src/app/login.tsx'
    s = content[p]
    s = change(s,
        "import { showToast } from '@/components/ui/toast';\n",
        "import { showToast } from '@/components/ui/toast';\n"
        "import { runAutoDailySignIn } from '@/features/account/auto-sign-in';\n", p)
    s = change(s,
        "  function finishLogin() {\n    showToast('登录成功');\n    router.back();\n  }\n",
        "  function finishLogin() {\n    showToast('登录成功');\n"
        "    // A user who logs in without restarting should also receive today's benefit.\n"
        "    void runAutoDailySignIn();\n    router.back();\n  }\n", p)
    content[p] = s

    p = 'src/app/settings.tsx'
    s = content[p]
    s = change(s,
        "import { Alert, Modal, Platform, Pressable, ScrollView, StyleSheet } from 'react-native';\n",
        "import { Alert, Modal, Platform, Pressable, ScrollView, StyleSheet, Switch } from 'react-native';\n", p)
    s = change(s,
        '  const { themeMode, accentId } = useSettings();\n',
        '  const { themeMode, accentId, autoDailySignIn } = useSettings();\n', p)
    anchor = '            <SectionHeader title="通用" />\n'
    ui = (
        '            <YStack backgroundColor={palette.card} borderRadius={20}\n'
        '              borderWidth={StyleSheet.hairlineWidth} borderColor={palette.border}\n'
        '              paddingHorizontal={14} paddingVertical={8}>\n'
        '              <XStack alignItems="center" justifyContent="space-between" minHeight={48}>\n'
        '                <YStack flex={1} gap={3} paddingRight={10}>\n'
        '                  <Text color={palette.text} fontSize={14.5}>打开应用自动签到并升级</Text>\n'
        '                  <Text color={palette.textTertiary} fontSize={11.5}>每天自动领取畅听 VIP 并升级概念版 VIP</Text>\n'
        '                </YStack>\n'
        '                <Switch value={autoDailySignIn}\n'
        '                  onValueChange={settingsActions.setAutoDailySignIn}\n'
        '                  trackColor={{ false: palette.border, true: palette.accent }} />\n'
        '              </XStack>\n'
        '            </YStack>\n'
    )
    s = change(s, anchor, anchor + ui, p)
    content[p] = s

    new_file = 'src/features/account/auto-sign-in.ts'
    code = (patch_root / 'source' / new_file).read_text(encoding='utf-8')
    if (root / new_file).is_file() and (root / new_file).read_text(encoding='utf-8') != code:
        raise ValueError('Automatic sign-in implementation already exists but is different; refusing to overwrite.')
    content[new_file] = code
    return content


def main():
    parser = argparse.ArgumentParser(description='Patch MoeKoeMusic-Mobile for daily auto claim and VIP upgrade')
    parser.add_argument('repo', type=Path, help='MoeKoeMusic-Mobile repository directory')
    parser.add_argument('--check', action='store_true', help='validate only; write nothing')
    args = parser.parse_args()
    root = args.repo.expanduser().resolve()
    patch_root = Path(__file__).resolve().parent
    try:
        changes = plan(root, patch_root)
        dirty = [path for path, data in changes.items()
                 if not (root / path).exists() or (root / path).read_text(encoding='utf-8') != data]
        print('Validated. Files to update:', len(dirty))
        for path in dirty:
            print(' ', path)
        if args.check or not dirty:
            return 0
        backup_dir = root / f'.auto-dailyvip-backup-{datetime.now():%Y%m%d-%H%M%S}'
        for path in dirty:
            dest = root / path
            if dest.exists():
                copy_path = backup_dir / path
                copy_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, copy_path)
        for path in dirty:
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(changes[path], encoding='utf-8')
        print('Applied successfully. Backup:', backup_dir if backup_dir.exists() else '(no previous files)')
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print('Patch not applied:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
