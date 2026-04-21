#redeploy 4
import discord
from discord.ext import commands
import re
import os
import json
from flask import Flask
from threading import Thread

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Banner Bot is Online (Permanent Memory & Public)!"
def run_web(): app.run(host='0.0.0.0', port=7860)
def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- CONFIG, MEMORY & FONTS ---
EMOJI_NUMBERS = {
    '1': '<:1_:1485637352176091186>', '2': '<:2_:1485637375257346219>',
    '3': '<:3_:1485637398800105695>', '4': '<:4_:1485637421264801844>',
    '5': '<:5_:1485637441120637018>', '6': '<:6_:1485637468198801550>',
    '7': '<:7_:1485637494010679416>', '8': '<:8_:1485637515200168008>',
    '9': '<:9_:1485637543549603871>', '0': '<:0_:1485637330298474617>'
}

# The magical smallcaps translator
SMALLCAPS_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
)

def to_smallcaps(text):
    """Converts any standard text into smallcaps."""
    return str(text).translate(SMALLCAPS_MAP)

BOH_FILE = "boh_memory.json"

def load_boh(guild_id):
    if not os.path.exists(BOH_FILE): return 0
    with open(BOH_FILE, "r") as f:
        try: return json.load(f).get(str(guild_id), 0)
        except: return 0

def save_boh(guild_id, amount):
    data = {}
    if os.path.exists(BOH_FILE):
        with open(BOH_FILE, "r") as f:
            try: data = json.load(f)
            except: pass
    data[str(guild_id)] = amount
    with open(BOH_FILE, "w") as f:
        json.dump(data, f)

def format_boh(val):
    return "".join(EMOJI_NUMBERS.get(char, char) for char in str(abs(int(val))))

async def safe_delete_bot_msg(message):
    try: await message.delete()
    except: pass

class CBTrackerView(discord.ui.View):
    def __init__(self, current_boh):
        super().__init__(timeout=60)
        self.current_boh = current_boh

    @discord.ui.button(label="Send Club Bento Tracker", style=discord.ButtonStyle.secondary)
    async def send_tracker(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Paste the current CB Tracker message:")
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        
        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=45.0)
            original_text = msg.content
            
            # Find the old Namraa BOH and the old Total
            namraa_match = re.search(r'(• ɴᴀᴍʀᴀᴀ —\s*)(\d+)', original_text)
            total_match = re.search(r'(ᴛᴏᴛᴀʟ:\s*)(\d+)', original_text)
            
            if namraa_match and total_match:
                old_namraa = int(namraa_match.group(2))
                old_total = int(total_match.group(2))
                
                # Calculate difference based on memory vs pasted text
                difference = self.current_boh - old_namraa
                new_total = old_total + difference
                
                # Replace the values in the text
                updated_text = re.sub(r'(• ɴᴀᴍʀᴀᴀ —\s*)\d+', rf'\g<1>{self.current_boh}', original_text)
                updated_text = re.sub(r'(ᴛᴏᴛᴀʟ:\s*)\d+', rf'\g<1>{new_total}', updated_text)
                
                await interaction.channel.send(updated_text)
            else:
                await interaction.followup.send("Could not find the 'ɴᴀᴍʀᴀᴀ' or 'ᴛᴏᴛᴀʟ' value in the text you pasted!")
        except:
            await interaction.followup.send("Error or timed out.")
        self.stop()


class BOHConfirmationView(discord.ui.View):
    def __init__(self, current_val, auto_change, guild_id, standalone=False):
        super().__init__(timeout=60)
        self.value = None
        self.final_change = auto_change
        self.current_val = current_val
        self.auto_change = auto_change
        self.guild_id = guild_id
        self.standalone = standalone

    @discord.ui.button(label="Use Auto Math", style=discord.ButtonStyle.green)
    async def confirm(self, interaction, button):
        self.value = self.current_val + self.auto_change
        save_boh(self.guild_id, self.value)
        
        if self.standalone:
            await safe_delete_bot_msg(interaction.message) 
            await interaction.response.send_message(f"✅ Kept BOH at: **{self.value}**")
        else:
            await interaction.response.edit_message(content=f"✅ Calculated! Proceeding with BOH: **{self.value}**", view=None)
        self.stop()

    @discord.ui.button(label="Manual Change", style=discord.ButtonStyle.blurple)
    async def manual_change(self, interaction, button):
        await interaction.response.send_message("Enter the **change** amount (use - for subtraction):")
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=30.0)
            self.final_change = int(msg.content.replace(' ', ''))
            self.value = self.current_val + self.final_change
            save_boh(self.guild_id, self.value)
            
            if self.standalone:
                await safe_delete_bot_msg(interaction.message)
                await interaction.followup.send(f"🔄 Manual Update! New BOH: **{self.value}**")
            else:
                await interaction.edit_original_response(content=f"🔄 Manual Update! Proceeding with BOH: **{self.value}**", view=None)
        except:
            self.value = self.current_val + self.auto_change
        self.stop()

    @discord.ui.button(label="Set Current BOH", style=discord.ButtonStyle.gray)
    async def change_base(self, interaction, button):
        await interaction.response.send_message("Enter the new **Base BOH** (Starting point):")
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await interaction.client.wait_for("message", check=check)
            self.current_val = int(re.sub(r'[^\d]', '', msg.content))
            self.value = self.current_val + self.auto_change
            save_boh(self.guild_id, self.value)
            
            if self.standalone:
                await safe_delete_bot_msg(interaction.message)
                await interaction.followup.send(f"📍 Base BOH set to: **{self.current_val}**")
            else:
                await interaction.edit_original_response(content=f"📍 Base BOH set to: **{self.current_val}**. Proceeding with: **{self.value}**", view=None)
        except: 
            self.value = self.current_val + self.auto_change
        self.stop()

class BannerSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def run_flow(self, interaction, type_label, pattern, is_subtraction=False):
        await safe_delete_bot_msg(interaction.message)
        
        await interaction.response.send_message(f"Send message for **{type_label}**:")
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=60.0)
            raw = msg.content
        except: 
            return await interaction.followup.send("Timed out.")
        
        match = re.search(pattern, raw)
        if not match: return await interaction.followup.send("Invalid format! Try again.")

        if "OHS" in type_label.upper():
            party, ign, price = match.groups()
            display_name = party
        else:
            ign, price = match.groups()[:2]
            display_name = ign
            
        auto_change = -int(price) if is_subtraction else int(price)
        last_boh = load_boh(interaction.guild_id)
        
        conf_view = BOHConfirmationView(last_boh, auto_change, interaction.guild_id)
        await interaction.followup.send(f"Last BOH: **{last_boh}** | Parsed Change: **{auto_change}**", view=conf_view)
        await conf_view.wait()
        
        if conf_view.value is not None:
            new_total = conf_view.value
            final_change = conf_view.final_change
            
            prefix = "-" if final_change < 0 else "+"
            symbol = "<a:p_arrowright02:955615840311607356>" if "Remittance" in type_label else "<a:arrowpink:952314882710192169>"
            target = "ᴅᴏɢꜱ" if "OHS" in type_label.upper() else "ᴍᴇ"
            
            if "Remittance" in type_label:
                await interaction.followup.send("Enter (Admin) name:")
                try:
                    admin_msg = await interaction.client.wait_for("message", check=check, timeout=30.0)
                    target = admin_msg.content
                except:
                    target = "Admin"

            # Apply Smallcaps formatting
            sc_header = to_smallcaps(type_label)
            sc_target = to_smallcaps(target)
            sc_display = to_smallcaps(display_name)

            # Bold specifically the text chunks to prevent markdown breaking the emojis
            first_line = f"<a:p_bow013:955613723781922827> **{sc_header}** {symbol} **{sc_target} :** <a:p_sparkles01:735706323198541904>"

            banner = (f"{first_line}\n"
                      f"{prefix}{abs(final_change)}ʙ <:p_moneybag01:735706322518933565> <:p_dot03:912428881577906276> {sc_display} <:p_dot03:912428881577906276> ʙᴏʜ : {format_boh(new_total)}")
            
            await interaction.channel.send(banner, view=CBTrackerView(new_total))

    @discord.ui.button(label="OHS Payment", style=discord.ButtonStyle.blurple)
    async def ohs(self, interaction, button):
        await self.run_flow(interaction, "OHS Payment", r'#(\d+)[ \t|•]+(.*?)[ \t|•]+(\d+)', True)

    @discord.ui.button(label="New Recruit's Payment", style=discord.ButtonStyle.green)
    async def recruit(self, interaction, button):
        await self.run_flow(interaction, "New Recruit's Payment", r'(.*?)[ \t|•]+(\d+)')

    @discord.ui.button(label="Renewal Payment", style=discord.ButtonStyle.green)
    async def renewal_p(self, interaction, button):
        await self.run_flow(interaction, "Renewal Payment", r'(.*?)[ \t|•]+(\d+)')

    @discord.ui.button(label="Renewal Remittance", style=discord.ButtonStyle.red)
    async def renewal_r(self, interaction, button):
        await self.run_flow(interaction, "Renewal Remittance", r'(.*?)[ \t|•]+(\d+)')


class BannerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def on_message(self, message):
        if message.author.bot: return

        is_namraa = message.author.id == 1003695708773298286

        if message.content.strip().upper() == "BOH":
            current_boh = load_boh(message.guild.id) 
            
            view = BOHConfirmationView(current_boh, auto_change=0, guild_id=message.guild.id, standalone=True)
            view.children[0].label = "Keep Current" 
            
            greeting = "Hi Namraa! The prettiest and bestest VP! 💖\n\n" if is_namraa else ""
            
            await message.channel.send(
                f"{greeting}💰 **Current BOH:** {current_boh}\n"
                f"Status: {format_boh(current_boh)}", 
                view=view
            )
            return

        # --- DIRECT TRACKER TRIGGER (NO BUTTON) ---
        if message.content.strip().upper() == "TRACKER":
            current_boh = load_boh(message.guild.id) 
            greeting = "Hi Namraa! The prettiest and bestest VP! 💖\n\n" if is_namraa else ""
            
            await message.channel.send(f"{greeting}Paste the current CB Tracker message:")
            
            def check(m): return m.author == message.author and m.channel == message.channel
            
            try:
                msg = await self.wait_for("message", check=check, timeout=45.0)
                original_text = msg.content
                
                namraa_match = re.search(r'(• ɴᴀᴍʀᴀᴀ —\s*)(\d+)', original_text)
                total_match = re.search(r'(ᴛᴏᴛᴀʟ:\s*)(\d+)', original_text)
                
                if namraa_match and total_match:
                    old_namraa = int(namraa_match.group(2))
                    old_total = int(total_match.group(2))
                    
                    difference = current_boh - old_namraa
                    new_total = old_total + difference
                    
                    updated_text = re.sub(r'(• ɴᴀᴍʀᴀᴀ —\s*)\d+', rf'\g<1>{current_boh}', original_text)
                    updated_text = re.sub(r'(ᴛᴏᴛᴀʟ:\s*)\d+', rf'\g<1>{new_total}', updated_text)
                    
                    await message.channel.send(updated_text)
                else:
                    await message.channel.send("Could not find the 'ɴᴀᴍʀᴀᴀ' or 'ᴛᴏᴛᴀʟ' value in the text you pasted!")
            except:
                await message.channel.send("Timed out waiting for the tracker.")
            return

        if self.user.mentioned_in(message) and not message.mention_everyone:
            greeting = "Hi Namraa! The prettiest and bestest VP! 💖 Select a banner:" if is_namraa else "Select a banner:"
            await message.channel.send(greeting, view=BannerSelectionView())

        await self.process_commands(message)

if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if token: BannerBot().run(token)
