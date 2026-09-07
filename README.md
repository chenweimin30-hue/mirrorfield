# 镜原 Mirrorfield · 联机版

草原上竖立无数面镜子，在镜林中找到对方并开击。子弹会沿镜面 45° 反弹。
支持 **最多 10 名真实玩家** 同房实时对战，手机 / 电脑 / 桌面 APP（PWA）三端通用。

---

## 一、启动游戏服务器

游戏依赖自带的零依赖 Node 服务器（静态文件 + WebSocket + 权威模拟，30Hz）。

```powershell
cd D:\WorkBuddy\2026-09-06-16-32-05\mirrorfield
C:\Users\mini\.workbuddy\binaries\node\versions\22.22.2\node.exe server.js
```

看到 `镜原联机服务器已启动` 即成功。此时：

| 场景 | 访问地址 |
|---|---|
| 本机 | http://localhost:8080 |
| 同一 WiFi 的手机 / 电脑 | http://192.168.0.102:8080 （局域网 IP，用 `ipconfig` 查 `WLAN` 一栏确认） |

> 联机时**必须**通过这个服务器打开页面。直接双击 `index.html` 用 `file://` 打开只能单机。

---

## 二、全国联机（0 预算）

### 为什么不能"在自己电脑上开个端口让全国的人进"？

已实测本机网络环境：

| 项目 | 实测结果 | 结论 |
|---|---|---|
| 公网 IPv6 | **无**（所有网卡只有 `fe80::` 本地链路地址） | 不能靠 IPv6 直连 |
| 本机 IPv4 | `192.168.0.102`（路由器内网） | 不是公网地址 |
| 出口公网 IPv4 | `27.26.102.14`（家宽，位于运营商 CGNAT 之后） | 入站端口被封，外网无法主动连进来 |
| 有线网卡 | `169.254.x.x`（APIPA，未接入网络） | 不可用 |

**结论：自己做端口映射 / DDNS 这条路走不通。** 家宽没有真正的公网 IP，路由器上开端口转发外网也进不来。

### 正确做法：免费内网穿透（中继）

让本机主动"向外"连到一家免费穿透服务商，由它分配一个 **公网 `https://` 网址**，全国任何人的浏览器打开这个网址就能进你的房间。
**0 元、无需服务器、无需备案。** 游戏已适配：页面走 `https://` 时，WebSocket 自动升级为 `wss://`（见 `index.html` 的 `wsConnect()`）。

#### 方案 A：cpolar（推荐，国产、速度快、注册即用）

1. 打开 https://www.cpolar.com 注册免费账号，进入后台复制你的 **authtoken**
2. 下载 Windows 客户端并解压，得到 `cpolar.exe`
3. 粘贴执行（换成你的 token）：

```powershell
cd <cpolar.exe 所在目录>
.\cpolar.exe authtoken 你的令牌
.\cpolar.exe http 8080
```

4. 终端会出现 `https://xxxxxx.r6.cpolar.cn` —— 这就是全国可访问的房间地址。

#### 方案 B：ngrok（国际老牌，免费档）

1. 注册 https://ngrok.com 免费账号，复制 authtoken
2. 下载客户端（国内可直接用 `https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip`）
3. 执行：

```powershell
.\ngrok.exe config add-authtoken 你的令牌
.\ngrok.exe http 8080
```

4. 得到 `https://xxxx.ngrok-free.app`。

#### 方案 C：Cloudflare Tunnel（**免注册**，但下载较慢）

不需要任何账号，代价是网址每次重启都会变：

```powershell
.\cloudflared.exe tunnel --url http://localhost:8080
```

得到 `https://xxxx.trycloudflare.com`。
二进制下载：GitHub 在本机网络时常被重置，可用国内镜像：

```powershell
curl -L -o cloudflared.exe "https://ghproxy.net/https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
```

> 实测该镜像约 14KB/s 且可能中途断开，52MB 需要较长时间；若下不动请改用方案 A。

### 分享房间

游戏菜单里点 **「复制房间链接」** 按钮，把链接发给朋友即可（微信、QQ 直接发）。
也可以直接把地址栏的网址复制给对方——**同一条链接，全国同服**。

### 注意事项

- **服务器和穿透窗口都要保持开着**，关掉任一个，房间就没了。
- 免费档的网址是**随机且会变**（cpolar 约 24 小时变一次，ngrok/cloudflared 每次重启都变）。想要固定网址，cpolar 有每月十几元的固定域名套餐；纯 0 预算就每次重新复制链接。
- 10 人满了会提示房间已满，等一局结束（2 分钟）再进。
- 手机把该网址 **添加到主屏幕** 即变成全屏 APP 体验（已内置 PWA，需 `https://`）。

---

## 三、玩法

- **目标**：在镜林中找到对手并击杀。击杀 / 反弹命中得分，2 分钟一局，结算后进下一局
- **人机关卡**：从 1 名电脑敌人开始，每过一关敌人数量 +1，最高 20 名；电脑会追击、游走、直射和镜面反弹射
- 房间满 2 人即开 8 秒等待 → 3 秒倒计时 → 开打
- 子弹沿镜面 45° 反弹（`/` 与 `\` 两种镜面），白色虚线为最多 3 次反弹的预测弹道
- 被击中后短暂无敌（闪烁），死亡 2 秒后于远离敌人的位置重生
- 进入游戏前可设置 **允许子弹打破镜子**（联机时由服务器同步给全房间）
- 道具随机刷新：**治疗 / 激光增强 / 三连发 / 护盾 / 穿甲**

### 操作

| | 电脑 | 手机 |
|---|---|---|
| 移动 | `WASD` | 左侧虚拟摇杆 |
| 瞄准 | 鼠标 | 右侧摇杆（松手自动瞄准最近敌人） |
| 射击 | 左键 / 空格 | 右侧摇杆 |
| 冲刺 | `Shift` | 冲刺按钮 |
| 暂停 / 静音 | `P` / `M` | 右上角按钮 |

---

## 四、构建原生 APP

仓库已提供完整的构建支持，详见 **[BUILD_APP.md](./BUILD_APP.md)**。

支持方式：

1. **GitHub Actions 自动打包 APK（推荐）**
   - 打开仓库 [Actions](https://github.com/chenweimin30-hue/mirrorfield/actions) → **Build Android APK** → **Run workflow**
   - 选择 `debug`（默认可直接安装）或 `release`（需配置签名 Secrets）
   - 构建完成后在 Artifacts 下载 APK
2. **PWA 安装**：浏览器打开后「添加到主屏幕」
3. **PWABuilder 在线生成 APK**：适合无本地环境时快速出包
4. **Capacitor 本地构建**：适合上架与深度定制

本地 Capacitor 快速开始：

```bash
npm install
npm run prepare:www
npx cap add android
npx cap sync
npx cap open android
```

---

## 五、文件说明

| 文件 | 作用 |
|---|---|
| `server.js` | 零依赖服务器：静态服务 + 手写 RFC6455 WebSocket + 30Hz 权威模拟 |
| `index.html` | 游戏客户端（Canvas 渲染、联机同步、三端输入、PWA） |
| `sw.js` / `manifest.json` / `icon.svg` | PWA 离线与桌面图标支持 |
| `package.json` / `capacitor.config.json` | Capacitor 构建配置（生成 Android / iOS APP） |
| `.github/workflows/build-android.yml` | GitHub Actions 自动构建 APK |
| `BUILD_APP.md` | 原生 APP 构建完整指南 |
| `tunnel/` | 放穿透客户端（如 cpolar.exe）的目录，已加入 .gitignore |
