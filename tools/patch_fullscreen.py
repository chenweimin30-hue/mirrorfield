import sys
import re

path = sys.argv[1]
with open(path) as f:
    src = f.read()

print("Original file content:")
print(src)
print("---")

inject = '''
        // 沉浸式全屏：隐藏状态栏和导航栏
        android.view.View decorView = getWindow().getDecorView();
        int uiOptions = android.view.View.SYSTEM_UI_FLAG_FULLSCREEN
                | android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                | android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | android.view.View.SYSTEM_UI_FLAG_LAYOUT_STABLE;
        decorView.setSystemUiVisibility(uiOptions);
'''

# 用正则匹配 super.onCreate(...)，兼容不同格式
pattern = r'(super\.onCreate\([^)]+\);)'
match = re.search(pattern, src)
if match:
    print(f"Found: {match.group(1)}")
    src = re.sub(pattern, match.group(1) + inject, src, count=1)
    print("Patched successfully")
else:
    print("WARNING: super.onCreate not found, trying onCreate method...")
    # 备用：在 onCreate 方法的 { 后注入
    pattern2 = r'(public void onCreate\(Bundle savedInstanceState\)\s*\{)'
    match2 = re.search(pattern2, src)
    if match2:
        src = re.sub(pattern2, match2.group(1) + inject, src, count=1)
        print("Patched via onCreate method")
    else:
        print("ERROR: Could not find injection point")
        sys.exit(1)

with open(path, "w") as f:
    f.write(src)

print("---")
print("Patched file content:")
print(src)
print("Patched OK")
