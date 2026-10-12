# ms from the first sound; a bar is 2000 ms
# bars 1-3: a part with no level is mf, as one marked mf; ff is 10 dB louder
louder 440 200 1800 2200 3800 -1
louder 440 2200 3800 200 1800 -1
louder 440 4200 5800 2200 3800 8
# bars 4-8: pp holds over three bars, then ff holds over two; 20 dB apart
flat 440 6250 11750 1.5
flat 440 12250 15750 1.5
louder 440 14200 15800 6200 7800 18
# bars 9-12: pp < ff and ff > pp, each over two bars
rising 440 16250 19750 18
falling 440 20250 23750 18
# bars 13-14: `gain -12` is 12 dB down
louder 440 26200 27800 24200 25800 11
louder 440 24200 25800 26200 27800 -13
# bars 15-16: 16 parts, 29 voices, at pp: quiet in absolute terms
rms 28200 31800 -80 -35
# bars 17-18: the same at ff
rms 32200 35800 -24 -3
louder 0 32200 35800 28200 31800 18
noclip
