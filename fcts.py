import youtube_dl
import requests


def get_status(filename: str) -> list:
    status = []
    with open(filename) as f:
        for line in f.readlines():
            status.append(line.strip())
    
    return status


is_mod = lambda member: True if "MODERATEUR" in [role.name for role in member.roles] else False
get_content = lambda context: list(map(lambda s: s.lower(), context.message.content.split(" ")))[1:]


# VIDEO STUFF
music_queue = []  # In building state
ydl_opts = {
    'format': "bestaudio/best",
    'postprocessor': [{
        'key': "FFmpegExtractAudio",
        'preferredcodec': "mp3",
        'preferredquality': '192'
    }],
    'restrictfilenames': True
}


def get_url(name: list) -> str:
    if not name:
        return None

    re = requests.get(f"https://www.youtube.com/results?search_query={'+'.join(name)}")

    first_vid = re.text.split('videoId":')[1]                       # Getting the first video block
    video_id = first_vid.split(',"thumbnail"')[0].split('\"')[1]    # Extracting the id
    
    return f"https://www.youtube.com/watch?v={video_id}"


def download_song(url: str):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
