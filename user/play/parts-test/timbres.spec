# ms from the first sound; bar k starts at (k - 1) x 2000
# strings: a bowed string's strong second harmonic
present 220 200 1800 -20 250
ratio 220 440 200 1800 -12 6
# horn: round; trumpet brighter (its sixth harmonic); trombone sounds
present 220 2200 3800 -20 250
brighter 220 1320 2200 3800 4200 5800 3
present 220 6200 7800 -20 250
# clarinet: odd harmonics, the even ones weak
ratio 220 440 8200 9800 -80 -12
ratio 220 660 8200 9800 -15 3
# oboe: the second harmonic over a weak fundamental
ratio 220 440 10200 11800 0 20
# flute: nearly a sine
ratio 220 440 12200 13800 -40 -8
# organ: the 4' (second harmonic) strong
ratio 220 440 14200 15800 -10 6
# pedal: the 16' an octave under the written note
present 110 16200 17800 -20 250
# choir: "ah", the formants near 750-1150 Hz over 2 kHz
ratio 880 1980 18200 19800 -80 -8
present 220 18200 19800 -30 250
# voice: a solo singer's vibrato
vibrato 220 20300 21800 0.5 3
# harp: plucked, it dies away
louder 220 22050 22300 23500 23900 6
# timpani at A2: its 1.504 mode; it dies away
present 165.4 26050 26800 -30 250
louder 110 26050 26300 27500 27900 4
# bells at A4: hum (A3) and tierce (1.2 x 440); a long ring
present 220 30100 31800 -30 250
present 528 30100 31800 -30 250
# tam-tam: blooms after the stroke
rising 331 34000 34750 2
present 331 34500 35500 -25 250
# cymbal: a crash, bright, dying away
present 8000 40050 40500 -50 250
louder 0 40050 40300 41500 41900 6
# bass drum: its low mode
present 52 44050 44500 -20 250
noclip
