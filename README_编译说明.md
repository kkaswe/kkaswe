# MoeKoe Music Mobile 自动领取 + 自动升级版 — APK 构建套件

## 当前交付状态

这是**完整的 GitHub Actions Android APK 构建套件**，不是已经编译好的 APK。本环境无法连接 GitHub/npm，且没有 Android SDK，因此没有构建 Android 二进制，也没有设备实测。任何名为 `.apk` 的文件，必须是后续 GitHub Actions 成功运行实际产生的，不要误把本 ZIP 当成 APK。

已核实上游项目固定源代码版本：`ab71195d4cf3297332490fd37704d1ae8973d4c5`（原项目 `package.json` 为 1.1.0；**不是** `v1.1.0` 发布标签的源码快照）。这能保证补丁定位的原函数兼容；构建需要 GitHub Actions 对 GitHub/npm/Gradle 的联网访问。

## 无需电脑安装 Android Studio：使用 GitHub Actions 编译

1. 登录 GitHub，创建**新的空白仓库**，例如 `moekoe-autovip-build`。建议私有仓库。
2. 把本 ZIP **解压**，把 `.github/workflows/build-android-apk.yml`、`patch/`、`scripts/`、本说明文件按原目录结构提交到该仓库。注意必须是文件，而不是只上传压缩包。GitHub 网页上传时要确认隐藏目录 `.github` 也被上传；也可使用 GitHub Desktop 或 Git 命令提交。
3. 打开该仓库的 **Actions → Build MoeKoe AutoVIP APK → Run workflow**，选择默认分支并运行。
4. 构建成功后打开运行记录，下载名称为 **MoeKoe-AutoVIP-APK** 的 Artifact ZIP，解压得到 `MoeKoe-AutoVIP-1.1.0-arm64-release.apk` 以及 `SHA256SUMS.txt`。APK 下载页面只会在流程成功后出现。
5. 把 APK 传到荣耀 Magic V5，打开安装（无需 Root）。安装后首次登录酷狗账号。必须联网，活动领取与升级能否成功由酷狗服务端决定。

如 Actions 未显示该工作流，检查上传后文件实际路径是否为仓库根目录下 `.github/workflows/build-android-apk.yml`，以及仓库 Settings → Actions 是否允许执行工作流。私人仓库可能受 GitHub Actions 配额约束。

## 自动权益逻辑

- 启动 App、切回前台、成功登录后（需在设置中开启）触发。
- 每个账号每天先请求 `signInDailyVip()` 领取一天畅听 VIP，再通过 `upgradeDailyVip()` 请求升级概念版 VIP。
- 领取与升级独立记录；升级失败时不会再次领取。
- 成功或平台提示已经完成则跳过；请求失败冷却 60 分钟；明确出现风控当天暂停。
- 每日划分为北京时间 UTC+8；前台触发，而非后台定时任务。
- “设置 → 通用 → 打开应用自动签到并升级”提供开关，默认打开。

## 与官方 APK 共存及升级注意事项

构建流程将 Android package 改为 `cn.moekoe.music.autovip`、应用显示名改为 `MoeKoe AutoVIP`，**不会覆盖原版** `cn.moekoe.music`。原版的本地会话、下载缓存不会自动迁移；在新 App 中重新登录账号。构建使用上游的 debug 签名配置执行 release 打包，属于测试/自用签名，不是官方签名。日后若更换签名证书不能直接覆盖安装。建议确认稳定后保存密钥进行正式签名。

**重要：** 原版 `app.json` 含指向上游的 Expo OTA 更新配置。本套件在编译前明确设置 `updates.enabled=false` 且移除原 Expo EAS 项目关联，避免从上游 OTA 覆盖自定义签到代码。这也表示修改版不会获得原版 OTA 更新，需要自己重新构建新版。

本项目 GPL-2.0-only；再分发修改版 APK 时请遵守相应许可证和源代码提供义务。本构建套件仅包含补丁，构建时会克隆上游源码（https://github.com/MoeKoeMusic/MoeKoeMusic-Mobile）。

## 无法正常编译的常见原因

- **Clone 失败：** GitHub Actions 无法访问 GitHub；重试或检查仓库网络/Actions 开关。
- **npm 依赖失败：** 上游某个依赖、API 子模块版本失效；检查对应失败日志，不能单纯跳过。
- **Gradle 失败：** 查看 SDK、NDK 与 Java 的详细错误；此套件基于上游 Android Release 工作流（Java 17、Gradle assembleRelease、arm64-v8a）改写。
- **安装冲突：** 应用的包名已隔离；如果曾安装过由不同证书签署的自定义同包名应用，先备份并卸载旧版。
- **签到不能成功：** 平台接口/权益问题，不等于安装包编译错误；遇到风控不要反复尝试。

## 验证记录

- 先前补丁已通过本地模拟签到、升级与重复执行测试，以及补丁幂等测试。
- 该 GitHub Actions workflow 为基于上游官方 workflow 制作的构建方案，**尚未在本会话实际执行成功**，因此不能保证首次云端构建一遍通过。
