import os
import discord
from discord.ext import commands, tasks
from datetime import datetime
import pytz
import json

# Setup bot
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='$', intents=intents)

REMINDER_DIR = 'reminders/'
TIMEZONE_FILE = 'user_timezones.json'

if not os.path.exists(REMINDER_DIR):
    os.makedirs(REMINDER_DIR)

# Load or initialize user timezones
if os.path.exists(TIMEZONE_FILE):
    with open(TIMEZONE_FILE, 'r') as f:
        user_timezones = json.load(f)
else:
    user_timezones = {}

# Helper: Save user timezones
def save_timezones():
    with open(TIMEZONE_FILE, 'w') as f:
        json.dump(user_timezones, f)

# Helper: Parse time string and localize
def parse_time(time_str, tz):
    try:
        user_time = datetime.strptime(time_str, "%I:%M %p")
        now = datetime.now(pytz.timezone(tz))
        user_time = user_time.replace(year=now.year, month=now.month, day=now.day)
        return pytz.timezone(tz).localize(user_time)
    except ValueError:
        return None

# Save reminder
def save_reminder(user_id, task, time_str):
    file_path = os.path.join(REMINDER_DIR, f"{user_id}_reminders.txt")
    with open(file_path, "a") as file:
        file.write(f"{task} at {time_str}\n")

# List timezones
@bot.command()
async def list_timezones(ctx):
    await ctx.send("🌍 You can find valid timezone strings here:\nhttps://en.wikipedia.org/wiki/List_of_tz_database_time_zones")

# Set timezone
@bot.command()
async def set_timezone(ctx, timezone: str):
    if timezone not in pytz.all_timezones:
        await ctx.send("❌ Invalid timezone. Use `$list_timezones` to find valid options.")
        return
    user_timezones[str(ctx.author.id)] = timezone
    save_timezones()
    await ctx.send(f"✅ Your timezone has been set to `{timezone}`")

# Add reminder
@bot.command()
async def add_reminder(ctx, *, input_text: str):
    user_id = str(ctx.author.id)
    if user_id not in user_timezones:
        await ctx.send("🌍 Please set your timezone first using `$set_timezone <Timezone>`.")
        return

    default_time = '12:00 PM'
    if ' at ' in input_text:
        task, time_str = input_text.rsplit(' at ', 1)
    else:
        task = input_text
        time_str = default_time

    tz = user_timezones[user_id]
    reminder_time = parse_time(time_str, tz)

    if reminder_time:
        save_reminder(user_id, task, time_str)
        embed = discord.Embed(
            title="📌 Reminder Set",
            description=f"**📝 Task:** {task}\n**⏰ Time:** {time_str} ({tz})",
            color=discord.Color.green()
        )
        embed.set_footer(text="⏳ We'll remind you on time!")
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Invalid time format. Please use HH:MM AM/PM format.")

# List reminders
@bot.command()
async def list_reminders(ctx):
    user_id = str(ctx.author.id)
    file_path = os.path.join(REMINDER_DIR, f"{user_id}_reminders.txt")
    if not os.path.exists(file_path):
        await ctx.send("📭 You have no reminders.")
        return

    with open(file_path, "r") as file:
        reminders = file.readlines()

    if reminders:
        embed = discord.Embed(title="📋 Your Reminders", color=discord.Color.blue())
        for i, line in enumerate(reminders, 1):
            embed.add_field(name=f"#{i}", value=line.strip(), inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("📭 You have no reminders.")

# Delete reminder
@bot.command()
async def delete_reminder(ctx, index: int):
    user_id = str(ctx.author.id)
    file_path = os.path.join(REMINDER_DIR, f"{user_id}_reminders.txt")

    if not os.path.exists(file_path):
        await ctx.send("📭 You have no reminders to delete.")
        return

    with open(file_path, "r") as file:
        lines = file.readlines()

    if 1 <= index <= len(lines):
        removed = lines.pop(index - 1)
        with open(file_path, "w") as file:
            file.writelines(lines)
        await ctx.send(f"🗑️ Deleted reminder: `{removed.strip()}`")
    else:
        await ctx.send("❌ Invalid index. Use `$list_reminders` to see valid indexes.")

# Reminder Checker Loop
@tasks.loop(seconds=30)
async def check_reminders():
    for filename in os.listdir(REMINDER_DIR):
        if filename.endswith("_reminders.txt"):
            user_id = filename.split("_")[0]
            file_path = os.path.join(REMINDER_DIR, filename)
            if user_id not in user_timezones:
                continue  # Skip users without timezones set

            tz = user_timezones[user_id]
            now = datetime.now(pytz.timezone(tz))

            with open(file_path, "r") as file:
                lines = file.readlines()

            new_lines = []
            for line in lines:
                if " at " not in line:
                    continue
                task, time_str = line.strip().rsplit(" at ", 1)
                reminder_time = parse_time(time_str.strip(), tz)

                if reminder_time and abs((reminder_time - now).total_seconds()) < 60:
                    user = await bot.fetch_user(int(user_id))
                    embed = discord.Embed(
                        title="🔔 Reminder Time!",
                        description=f"**📝 Task:** {task}\n**⏰ Time:** {time_str} ({tz})",
                        color=discord.Color.red()
                    )
                    embed.set_footer(text="Stay productive!")
                    try:
                        await user.send(embed=embed)
                    except:
                        print(f"❌ Couldn't DM user {user_id}")
                else:
                    new_lines.append(line)

            with open(file_path, "w") as file:
                file.writelines(new_lines)

# Bot Ready Event
@bot.event
async def on_ready():
    print(f"{bot.user.name} is online and smexy 😎")
    check_reminders.start()
bot.run('MTM1ODk3MzI4MjY5MDI3MzI4Mg.GKxLir.HDG8iDnaOivP3e_kCH8_hIVyQKAfm-1LD5yvRc')
