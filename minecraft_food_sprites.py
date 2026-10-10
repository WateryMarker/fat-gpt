"""Load Minecraft Java 1.21.4 textures bundled in assets/minecraft.

Original sources and SHA-256 checksums are recorded in sources.json.
Textures belong to Mojang / Microsoft; this is an unofficial fan project.
"""
from pathlib import Path
import tkinter as tk

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "minecraft"
FOOD_NAMES = {
    "steak": "สเต๊ก", "porkchop": "หมูย่าง", "bread": "ขนมปัง",
    "carrot": "แครอต", "cookie": "คุกกี้", "golden_apple": "แอปเปิลทอง",
}
TEXTURE_FILES = {
    "steak": "cooked_beef.png", "porkchop": "cooked_porkchop.png",
    "bread": "bread.png", "carrot": "carrot.png", "cookie": "cookie.png",
    "golden_apple": "golden_apple.png", "tnt": "tnt_side.png",
    "clock": "clock_00.png", "armor": "iron_chestplate.png", "chicken": "cooked_chicken.png",
    "shears": "shears.png", "paper": "paper.png", "stone": "cobblestone.png",
    "sword": "diamond_sword.png", "pickaxe": "iron_pickaxe.png", "book": "writable_book.png",
    "potion": "potion.png", "blaze": "blaze_powder.png", "slime": "slime_ball.png",
    "voice_on": "redstone_torch.png", "voice_off": "redstone_torch_off.png",
    "note": "note_block.png", "pearl": "ender_pearl.png",
}


def build_food_sprites(master):
    return {
        name: tk.PhotoImage(master=master, file=str(ASSET_DIR / filename))
        for name, filename in TEXTURE_FILES.items()
    }
