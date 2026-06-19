import sys
import re

def ModLoader_inject(html_path):
        with open(html_path, 'r', encoding='utf-8') as file:
            html = file.read()
        html = html.replace('<meta name="viewport" content="width=device-width,initial-scale=1">',"""<meta name="viewport" content="width=device-width,initial-scale=1">
<script>
        window.modLoaderKeyConfigWinHookFunction = (loaderKeyConfig) => {
            // LocalStorageLoader
            loaderKeyConfig.config.set('modDataLocalStorageZipList', 'CoTmodDataLocalStorageZipList');
            loaderKeyConfig.config.set('modDataLocalStorageZip', 'CoTmodDataLocalStorageZip');

            // IndexDBLoader
            loaderKeyConfig.config.set('modDataIndexDBZipListHidden', 'CoTmodDataIndexDBZipListHidden');
            loaderKeyConfig.config.set('modDataIndexDBZipList', 'CoTmodDataIndexDBZipList');
            loaderKeyConfig.config.set('modDataIndexDBZip', 'CoTmodDataIndexDBZip');

            // RemoteLoader
            // loaderKeyConfig.config.set('modList.json', '/path/to/modList/CoT_modList.json');

            // BeautySelectorAddon
            loaderKeyConfig.config.set('BeautySelectorAddon_OrderSaveKey', 'CoT_BeautySelectorAddon_OrderSaveKey');
            };
</script>
		""")
        # Remove itch.io anti-hotlink script (causes APK WebView timeout in China)
        html = re.sub(r'<script[^>]*src="https://static\.itch\.io/htmlgame\.js"[^>]*></script>', '', html)

        with open(html_path, 'w', encoding='utf-8') as file:
            file.write(html)

if __name__ == "__main__":
    html = sys.argv[1]
    ModLoader_inject(html)
