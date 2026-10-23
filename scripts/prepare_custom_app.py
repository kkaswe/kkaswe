#!/usr/bin/env python3
"""Set a unique Android app id and turn off upstream OTA updates.

This avoids sideload-signature conflicts with the original MoeKoe build and
avoids unexpected remote JS updates overwriting the modified code.
"""
import json
import sys
from pathlib import Path


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    manifest = root / 'app.json'
    obj = json.loads(manifest.read_text(encoding='utf-8'))
    expo = obj['expo']
    assert expo['android']['package'] == 'cn.moekoe.music', 'Unknown base app: stop.'
    expo['android']['package'] = 'cn.moekoe.music.autovip'
    expo['android']['versionCode'] = max(int(expo['android'].get('versionCode', 1)), 3)
    expo['name'] = 'MoeKoe AutoVIP'
    expo['slug'] = 'moekoe-autovip'
    expo['scheme'] = 'moekoe-autovip'
    expo['updates'] = {'enabled': False}
    # Build offline with Gradle, independent of upstream EAS/OTA project identity.
    extras = expo.get('extra')
    if isinstance(extras, dict):
        extras.pop('eas', None)
    manifest.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    assert expo['updates']['enabled'] is False
    print('Build configuration prepared: cn.moekoe.music.autovip, upstream OTA disabled')


if __name__ == '__main__':
    main()
