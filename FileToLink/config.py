import os


class Config:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    Token = os.environ.get("BOT_TOKEN", "")
    Session = os.environ.get("Session_String", "")
    if not Session:
        Session = ":memory:"
    App_Name = os.environ.get("APP_NAME", "FileToLink")
    Port = int(os.environ.get("PORT", 8080))
    Archive_Channel_ID = int(os.environ.get("ARCHIVE_CHANNEL_ID", 0))
    Start_Message = os.environ.get("Start_Message", "Hello! Send me any file to get direct download and stream links.")
    Bot_Channel = os.environ.get("Bot_Channel_UserName", "")
    if Bot_Channel and Bot_Channel.startswith("@"):
        Bot_Channel = Bot_Channel[1:]
    elif Bot_Channel == "":
        Bot_Channel = None

    # Dynamic Render domain fallback
    URL = os.environ.get("URL", "https://cinetouch-stream-python.onrender.com")
    Link_Root = f"{URL.rstrip('/')}/"

    Download_Folder = "Files"
    Dev_Channel = "shadow_bots"
    Bot_UserName = None  # Will be set dynamically on startup
    Part_size = 1024 * 1024  # 1MB Pyrogram Part Size
    Buffer_Size = 512 * 1024  # 512KB Buffer
    Pre_Dl = 1
    Separate_Time = 4
    Sleep_Threshold = 60
    Max_Fast_Processes = 1


class Strings:
    start = Config.Start_Message
    dl_link = "🔗 Download LINK"
    st_link = "🎞 Stream LINK"
    generating_link = "**⏳ Generating Link...**"
    bot_channel = "📢 Bot Channel"
    dev_channel = "🤖 Developer"
    fast = "⚡️**The link has been updated to a fast link**"
    update_link = "⚡ Update To Fast Link"
    update_limited = (f"⛔ You can update just {Config.Max_Fast_Processes} link in one time, "
                      "please wait until previous update to complete")
    re_update_link = "🔄 Re-Updating the link"
    already_updated = "The link is already updated"
    wait_update = "⏳ Updating the link..."
    wait = "⏳ Please wait..."
    progress = "⏳ Progress"
    file_not_found = "⚠️File Not Found, Please resend it again"
    delete_manually_button = "⚠️You can delete it"
    delete_forbidden = "The bot can't delete messages older than 48 hours, you can delete this message manually"
    force_join = "⚠ Join Bot Channel to use this Bot"
