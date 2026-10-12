# ms from the first sound; tempo 120 (a bar 2000 ms) to bar 16
# bar 1: staccato sounds half its length
louder 440 40 200 330 480 25
# bars 2-3: an unmarked repeat parts (a gap); tenuto does not
dip 440 2500 10 99
dip 440 3000 10 99
dip 440 4500 0 6
dip 440 5000 0 6
modulated 2100 3900 1.5
# bars 4-5: a tie across the bar line is one note
dip 440 8000 0 1.5
# bar 6: a slur: each note at its place, no gap between
onset 554.37 10500 20
onset 659.26 11000 20
onset 880.00 11500 20
modulated 10100 11900 0 1
# bar 7: an accent; bar 8 sfz; bar 9 fp
louder 440 12000 12060 12300 12450 3
louder 440 14000 14080 14700 15500 6
louder 440 16000 16080 16700 17500 8
# bar 10: hard left and hard right
pan 440 18100 19800 20 200
pan 659.26 18100 19800 -200 -20
# bar 11: a chord in one part; the organ has no vibrato
present 261.63 20100 21800 -30 250
present 329.63 20100 21800 -30 250
present 392.00 20100 21800 -30 250
vibrato 261.63 20200 21800 0 0.3
# bar 12: the pedal sounds its 16' (C2) under the written C3
present 65.41 22100 23800 -20 250
present 130.81 22100 23800 -20 250
# bar 13: the horn brighter at ff than at p (its fourth harmonic)
brighter 261.63 1046.5 24100 24900 25100 25900 6
louder 261.63 25100 25900 24100 24900 10
# bar 14: the solo voice's vibrato
vibrato 440 26400 27800 0.5 3
# bar 15: bowed tremolo, then plain bowing
modulated 28100 28900 1.5
modulated 29100 29900 0 1
# bar 16: rit from 120 to 60 over the bar; bar 17's fermata holds A5
onset 523.25 30000 20
onset 587.33 30534 20
onset 659.26 31151 20
onset 698.46 31880 20
onset 783.99 32773 20
onset 880.00 34773 20
present 880.00 35000 38500 -30 250
onset 1046.50 38773 20
# bar 19 (tempo 60, a half note 2000 ms): C4 tied while E4,G4 move to F4,A4
dip 261.63 44773 0 4
onset 349.23 44773 20
onset 440.00 44773 20
present 329.63 43000 44500 -30 250
absent 329.63 45200 46500 -45 250
absent 392.00 45200 46500 -45 250
# bar 20, the same without the tie: C4 is struck again (a gap, then a new attack)
dip 261.63 48773 8 99
noclip
