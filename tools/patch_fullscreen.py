import sys

path = sys.argv[1]
with open(path) as f:
    src = f.read()

inject = '''
        android.view.View decorView = getWindow().getDecorView();
        int uiOptions = android.view.View.SYSTEM_UI_FLAG_FULLSCREEN | android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION | android.view.View.SYSTEM_UI_FLAG_LAYOUT_STABLE;
        decorView.setSystemUiVisibility(uiOptions);
'''
src = src.replace("super.onCreate(savedInstanceState);", "super.onCreate(savedInstanceState);" + inject)

with open(path, "w") as f:
    f.write(src)

print("Patched OK")
