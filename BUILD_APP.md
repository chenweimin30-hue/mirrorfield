# 镜原 Mirrorfield · 构建原生 APP 指南

本游戏是 **PWA + Node 服务器** 架构。支持三种方式获得「APP 体验」：

| 方式 | 难度 | 说明 | 推荐场景 |
|------|------|------|----------|
| **PWA 安装** | ⭐ 最简单 | 浏览器「添加到主屏幕」 | 日常使用、快速体验 |
| **PWABuilder 在线打包 APK** | ⭐⭐ | 无需本地环境，生成可安装 APK | 只想要 Android 安装包 |
| **Capacitor 本地构建** | ⭐⭐⭐ | 生成真正的 Android / iOS 工程 | 上架应用商店、深度定制 |

> **重要提示**：联机对战依赖 WebSocket 服务器。打包成 APP 后，单机/人机模式可离线游玩；联机需要能访问到你的服务器地址（或公网穿透地址）。

---

## 方式一：PWA 安装（已支持，零代码）

1. 启动服务器并做内网穿透（见 README），得到 `https://xxxx` 地址。
2. 手机浏览器打开该地址。
3. 菜单 → **添加到主屏幕** / **安装应用**。
4. 桌面会出现「镜原」图标，全屏运行。

电脑 Chrome / Edge 打开后，地址栏右侧也会出现「安装」按钮。

---

## 方式二：用 PWABuilder 在线生成 Android APK（推荐新手）

不需要安装 Android Studio，适合只想快速得到一个可安装的 APK。

### 步骤

1. 确保游戏能通过 **HTTPS 公网地址** 访问（用 cpolar / ngrok / Cloudflare Tunnel）。
2. 打开 [https://www.pwabuilder.com](https://www.pwabuilder.com)
3. 输入你的游戏 HTTPS 地址，点击 **Start**。
4. 等待检测通过后，点击 **Package for stores** → 选择 **Android**。
5. 填写信息（可保持默认）：
   - Package ID：`com.mirrorfield.game`
   - App name：`镜原 Mirrorfield`
   - 其他按提示即可
6. 点击 **Generate** / **Download**，下载生成的 zip。
7. 解压后里面有 `app-release-signed.apk`（或类似名称），直接传到手机安装即可。

> 注意：免费穿透地址会变，APK 里写死的地址也会失效。若要长期使用，建议用固定域名或后续改用 Capacitor 并配置可修改的服务器地址。

---

## 方式三：Capacitor 本地构建（真正的原生工程）

适合想上架 Google Play / App Store，或需要改包名、图标、权限的开发者。

### 前置要求

- Node.js 18+
- 构建 Android：安装 [Android Studio](https://developer.android.com/studio)
- 构建 iOS：需要 macOS + Xcode

### 快速开始

```bash
# 1. 进入项目目录
cd mirrorfield

# 2. 安装依赖
npm install

# 3. 添加 Android 平台（首次）
npx cap add android

# 4. 同步网页资源到原生工程
npx cap sync

# 5. 用 Android Studio 打开工程
npx cap open android
```

在 Android Studio 中：

1. 等待 Gradle 同步完成。
2. 连接真机或启动模拟器。
3. 点击绿色 Run 按钮即可安装运行。
4. 要生成正式 APK / AAB：菜单 **Build → Generate Signed Bundle / APK**。

iOS 同理：

```bash
npx cap add ios
npx cap sync
npx cap open ios
```

### 常用命令（已写入 package.json）

```bash
npm run cap:sync          # 同步最新网页代码到原生工程
npm run build:android     # 同步并打开 Android Studio
npm run build:ios         # 同步并打开 Xcode
```

### 联机服务器地址配置

默认 APP 会加载本地打包的 `index.html`。如果希望 APP 直接连接你的公网服务器（而不是本地静态文件），可以修改 `capacitor.config.json`：

```json
{
  "server": {
    "url": "https://你的穿透地址",
    "cleartext": true
  }
}
```

然后重新执行 `npx cap sync`。

---

## 图标与清单优化建议

当前使用 SVG 图标。若要提升应用商店兼容性，建议额外准备：

- `icon-192.png`（192×192）
- `icon-512.png`（512×512）
- 带安全区的 maskable 图标

可把它们放在项目根目录，并更新 `manifest.json` 的 `icons` 字段。

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `package.json` | Capacitor 依赖与构建脚本 |
| `capacitor.config.json` | Capacitor 配置（包名、主题色等） |
| `BUILD_APP.md` | 本构建说明 |
| `manifest.json` / `sw.js` | 已有的 PWA 支持 |

构建产生的 `android/`、`ios/`、`node_modules/` 已建议加入 `.gitignore`，不提交到仓库。
