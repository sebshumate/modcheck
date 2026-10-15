import sys
from pathlib import Path
from unittest import loader
import zipfile
import json
import tomllib

folder = Path(sys.argv[1])
if not folder.exists():
    print(f"Folder {folder} does not exist")
    sys.exit(1)

jars = list(folder.glob("*.jar"))
print("Found", len(jars), "mods")


for jar in jars:
    with zipfile.ZipFile(jar) as z:
        names = z.namelist()
        loaders = []
        if "fabric.mod.json" in names:
                    loaders.append("fabric")
        if "META-INF/neoforge.mods.toml" in names:
                    loaders.append("neoforge")
        if "META-INF/mods.toml" in names:
                    loaders.append("forge")
                
        
        if not loaders:
                    loaders.append("unknown")
        
        
        print(jar.name, "->", ", ".join(loaders))

        if "fabric.mod.json" in names:
            data = json.loads(z.read("fabric.mod.json"), strict=False)
            print ("    name:", data.get("name"))
            print ("    version:", data.get("version"))
            print ("    minecraft:", data.get("depends", {}).get("minecraft"))

        toml_file = None
        if "META-INF/neoforge.mods.toml" in names:
            toml_file = "META-INF/neoforge.mods.toml"
        elif "META-INF/mods.toml" in names:
            toml_file = "META-INF/mods.toml"
        if toml_file and "fabric.mod.json" not in names: 
            info = tomllib.loads(z.read(toml_file).decode("utf-8"))
            mod = info["mods"][0]
            print ("    name:", mod.get("displayName"))
            print ("    version:", mod.get("version"))

     

        