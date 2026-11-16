#!/usr/bin/env python3
"""비즈 목소리 파일 → 대사 줄별 시작 시각(LINES) 계산.
쓰는 법: python3 voice_sync.py 목소리.mp4 대본.txt [출력.json]
- 대본.txt: 한 줄에 대사 하나(비즈에 넣은 원고와 같은 줄 수)
- 무음 구간(0.28초 이상)으로 문장을 나누고, 줄 수에 맞춰 가장 긴 쉼부터 경계로 고른다.
- 앞뒤 무음은 잘라 낸 voice.wav 도 같이 만든다(영상에 바로 입힘).
whisper 없이 ffmpeg 만 쓴다(클라우드에서 설치가 막혀 있어도 동작)."""
import json, re, subprocess, sys, os
src, script = sys.argv[1], sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else "lines.json"
lines = [l.strip() for l in open(script, encoding="utf-8") if l.strip()]
d = os.path.dirname(os.path.abspath(out))
wav = os.path.join(d, "voice_raw.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "48000", wav], check=True)
r = subprocess.run(["ffmpeg", "-i", wav, "-af", "silencedetect=noise=-38dB:d=0.28", "-f", "null", "-"], capture_output=True, text=True).stderr
dur = float(re.search(r"Duration: (\d+):(\d+):([\d.]+)", r).groups()[2]) + 60 * int(re.search(r"Duration: (\d+):(\d+)", r).groups()[1])
ss = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r)]
se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
sil = list(zip(ss, se + [dur] * (len(ss) - len(se))))
head = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0           # 앞 무음
tail = sil[-1][0] if sil and sil[-1][1] >= dur - 0.05 else dur  # 뒤 무음
inner = [(a, b) for a, b in sil if a > head + 0.1 and b < tail - 0.1]
need = len(lines) - 1
if len(inner) < need:
    sys.exit(f"쉼이 {len(inner)}개뿐이라 {len(lines)}줄로 못 나눠요. 비즈 원고 줄 사이에 [pause]를 넣어 다시 만들어 주세요.")
cut = sorted(sorted(inner, key=lambda x: x[1] - x[0], reverse=True)[:need])
starts = [0.0] + [round(b - head - 0.05, 2) for a, b in cut]
vend = round(tail - head, 2)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", f"atrim={head}:{tail},asetpts=PTS-STARTPTS,afade=t=in:d=0.03", os.path.join(d, "voice.wav")], check=True)
res = {"LINES": [[s, t] for s, t in zip(starts, lines)], "VEND": vend, "END": round(vend + 3.2, 2)}
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
