# px04 — what the census traces, pinned. Sourced inside the container.
# Archives by sha256 digest (refused on a mismatch); trees by commit.

# wolf 0.2.22, the release archive (builds boreutils, writes lobo's live site).
WOLF_URL=https://github.com/wolffe-lang/wolf-lang/releases/download/v0.2.22/wolf-0.2.22-x86_64-unknown-linux-gnu.tar.gz
WOLF_SHA256=df0f2fea26d9d26de5e577ee5d2cbabeaafe6d93ecfa447cb6be97ae442d8dba

# wolf-std: boreutils' and lobo's pin, re-derived against 0.2.22 (B151):
# every utility builds with --deny-warnings at this rev.
STD_REPO=https://github.com/wolffe-lang/wolf-std
STD_REV=14f0ab2c6a64e86240113e21c4da9f746380eb29

# boreutils trunk at px04's start (bu14 merged).
BORE_REPO=https://github.com/wolffe-lang/boreutils
BORE_REV=010f3144a9bae214f740aa2b2d33ea6e08794900

# lobo: the latest release archive, and its live site from trunk.
LOBO_URL=https://github.com/wolffe-lang/lobo/releases/download/v0.1.1/lobo-0.1.1-x86_64-unknown-linux-gnu.tar.gz
LOBO_SHA256=6e21e151987b2ede4df8591020368f39ec29033713523c29d99582fa39f2a7a0
LOBO_REPO=https://github.com/wolffe-lang/lobo
LOBO_REV=f79418d1181d47e987c35fc2a8efbbe0caa3984b

# The image's own pins (tools/census/Containerfile).
BASE_IMAGE_DIGEST=sha256:8185e444e45ba166146b244b41f1cba2d7d91f3eddce533a839cc9591e0fa785

# px81: pelt launch-trunk identity, read twice; tests/census C4 keeps
# the image pin and this census input together. This is not a live-head gate.
PELT_REPO=https://github.com/wolffe-lang/pelt
PELT_REV=4683b3f5faf46cd393ec2632f345f8cd483a4f1f

# px82 current-image snapshot; px04 trace inputs above remain historical.
# px97: yew trunk 2eb9cb9b, read again on 2026-11-06; red (C5) until the yew pin moves.
IMAGE_YEW_REV=2eb9cb9b2a8e33d788011aa6a81c3e633241c67c

# px82 current-image snapshot; px04 trace inputs above remain historical.
# px97: boreutils trunk ff5396ad, the sweep's; red (C5) until the boreutils pin moves.
IMAGE_BORE_REV=ff5396aded1ea37a3dbd321c2c625d30359a8e19

# px82 current-image snapshot; px04 trace inputs above remain historical.
# px97: scent trunk eb888dfc, the sweep's; red (C5) until the scent pin moves.
IMAGE_SCENT_REV=eb888dfc09cba931a747cc59c7c44ab549bd9997
