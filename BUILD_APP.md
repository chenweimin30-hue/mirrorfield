# 镜原 Mirrorfield · 构建原生 APP 指南

本游戏是 **PWA + Node 服务器** 架构。支持多种方式获得「APP 体验」。

| 方式 | 难度 | 说明 | 推荐场景 |
|------|------|------|----------|
| **PWA 安装** | ⭐ 最简单 | 浏览器「添加到主屏幕」 | 日常使用、快速体验 |
| **GitHub Actions 自动打包 APK** | ⭐⭐ | 推送代码或手动触发，自动出 APK | 持续集成、分发测试包 |
| **PWABuilder 在线打包 APK** | ⭐⭐ | 无需本地环境，生成可安装 APK | 只想要 Android 安装包 |
| **Capacitor 本地构建** | ⭐⭐⭐ | 生成真正的 Android / iOS 工程 | 上架应用商店、深度定制 |

> **重要提示**：联机对战依赖 WebSocket 服务器。打包成 APP 后，单机/人机模式可离线游玩；联机需要能访问到你的服务器地址（或公网穿透地址）。

---

## 方式〇：GitHub Actions 自动构建 APK（推荐）

仓库已内置工作流：`.github/workflows/build-android.yml`

### 如何触发

1. 打开仓库 **Actions** 页面
2. 左侧选择 **Build Android APK**
3. 点击 **Run workflow**
4. 选择构建类型：
   - `debug`：可直接安装的调试包（默认，无需任何配置）
   - `release`：正式签名包（需先配置 Secrets）
5. 运行结束后，在该次 Workflow 的 **Artifacts** 里下载 `mirrorfield-debug.apk` 或 `mirrorfield-release.apk`

也可以在推送 `main` 分支相关文件变更时自动构建 Debug 包；发布 GitHub Release 时尝试构建 Release 包。

### 配置正式签名（可选）

若要构建可长期更新的正式 APK，在仓库 **Settings → Secrets and variables → Actions** 中添加：

| Secret 名称 | 说明 |
|-------------|------|
| `ANDROID_KEYSTORE_BASE64` | keystore 文件的 base64 内容（`base64 -w0 your.keystore`） |
| `ANDROID_KEYSTORE_PASSWORD` | keystore 密码 |
| `ANDROID_KEY_ALIAS` | 密钥别名 |
| `ANDROID_KEY_PASSWORD` | 密钥密码 |

未配置时，选择 `release` 也会回退为 Debug 构建，不会失败。

### 生成 keystore 示例（本机）

```bash
keytool -genkeypair -v -keystore mirrorfield.keystore -alias mirrorfield -keyalg RSA -keysize 2048 -validity 10000
base64 -w0 mirrorfield.keystore > keystore.b64
# 把 keystore.b64 的内容粘贴到 ANDROID_KEYSTORE_BASE64
```

---

## 方式一：PWA 安装（已支持，零代码）

1. 启动服务器并做内网穿透（见 README），得到 `https://xxxx` 地址。
2. 手机浏览器打开该地址。
3. 菜单 → **添加到主屏幕** / **安装应用**。
4. 桌面会出现「镜原」图标，全屏运行。

电脑 Chrome / Edge 打开后，地址栏右侧也会出现「安装」按钮。

---

## 方式二：用 PWABuilder 在线生成 Android APK

不需要安装 Android Studio，适合只想快速得到一个可安装的 APK。

### 步骤

1. 确保游戏能通过 **HTTPS 公网地址** 访问（用 cpolar / ngrok / Cloudflare Tunnel）。
2. 打开 [https://www.pwabuilder.com](https://www.pwabuilder.com)
3. 输入你的游戏 HTTPS 地址，点击 **Start**。
4. 等待检测通过后，点击 **Package for stores** → 选择 **Android**。
5. 填写信息（可保持默认）：
   - Package ID：`com.mirrorfield.game`
   - App name：`镜原 Mirrorfield`
6. 点击 **Generate** / **Download**，下载生成的 zip。
7. 解压后安装 APK 即可。

> 注意：免费穿透地址会变，APK 里写死的地址也会失效。长期使用建议用固定域名，或用 Capacitor / Actions 构建本地资源包。

---

## 方式三：Capacitor 本地构建

适合想上架 Google Play / App Store，或需要改包名、图标、权限的开发者。

### 前置要求

- Node.js 18+
- 构建 Android：安装 [Android Studio](https://developer.android.com/studio)
- 构建 iOS：需要 macOS + Xcode

### 快速开始

```bash
cd mirrorfield
npm install
npm run prepare:www          # 把网页资源拷到 www/
npx cap add android          # 首次
npx cap sync
npx cap open android
```

在 Android Studio 中点击 Run，或 **Build → Generate Signed Bundle / APK**。

### 常用命令

```bash
npm run prepare:www       # 更新 www 静态资源
npm run cap:sync          # 同步到原生工程
npm run build:android     # 同步并打开 Android Studio
```

### 联机服务器地址（可选）

若希望 APP 直接加载公网服务器而不是内置静态页，可改 `capacitor.config.json`：

```json
{
  "server": {
    "url": "https://你的穿透地址",
    "cleartext": true
  }
}
```

然后重新 `npx cap sync`。

---

## 图标建议

当前使用 SVG 图标。上架建议额外准备：

- `icon-192.png`（192×192）
- `icon-512.png`（512×512）
- maskable 安全区图标

放到项目根目录后，更新 `manifest.json` 的 `icons`，并在 `prepare:www` 中一并拷贝。

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `.github/workflows/build-android.yml` | GitHub Actions 自动构建 APK |
| `package.json` | Capacitor 依赖与脚本 |
| `capacitor.config.json` | 包名、webDir=www、主题色 |
| `BUILD_APP.md` | 本构建说明 |
| `manifest.json` / `sw.js` | PWA 支持 |

构建产物 `android/`、`ios/`、`www/`、`node_modules/` 建议不提交（已在 `.gitignore`）。
