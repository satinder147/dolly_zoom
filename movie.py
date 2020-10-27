import math
from moviepy.editor import *
import moviepy.video.fx.all as vfx


class Editor:

    def __init__(self, name):
        self.name = name

    def process(self):
        speed = 2.5
        clip = VideoFileClip(self.name)
        duration = clip.duration//2
        start = duration//2
        end = start+duration
        part1 = clip.subclip(start, end)
        print(part1.duration)
        part2 = VideoFileClip(self.name).subclip(start, end)
        part2 = part2.fx(vfx.time_mirror)
        stacked = concatenate_videoclips([part1, part2])
        result = stacked.fl_time(lambda t: t*speed)
        result.duration = (part1.duration+part2.duration)/speed
        sound1 = AudioFileClip("sound1.mp3")
        print(sound1.duration - part1.duration/speed)
        sound1 = sound1.subclip(max(0, math.floor(sound1.duration - part1.duration/speed)), sound1.duration)
        sound2 = AudioFileClip("sound2.mp3")
        sound2 = sound2.subclip(0, min(math.floor(part2.duration/speed), sound2.duration))
        audio_combine = concatenate_audioclips([sound1, sound2])
        audio_combine = audio_combine.set_fps(30)
        result = result.set_audio(audio_combine)
        result.write_videofile("boomerang.mp4")


if __name__ == '__main__':
    Editor('res.mp4').process()

