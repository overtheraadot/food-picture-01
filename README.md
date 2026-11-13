# Steaming Ramen

![food-picture-01](https://make.fun/badge/food-picture-01.svg)
![rank](https://make.fun/badge/food-picture-01/rank/overtheraadot.svg)
![reward](https://make.fun/badge/food-picture-01/reward/overtheraadot.svg)

A steaming bowl of ramen, seen from a high angle on a dark wooden table
— one look and you want to eat it.

## The picture

Rich golden broth in a deep indigo bowl, a tangled nest of wavy noodles,
two halves of a soft-boiled egg with jammy orange yolks, pink-swirled
narutomaki, roasted chashu, a sheet of nori, scattered spring onions,
chili threads and sesame — with chopsticks lifting a curl of noodles
through curling steam. Warm, bright food against a dark table, no text:
it reads at a glance and still looks delicious at 300 px.

## How it is made

`main.py` draws the whole image procedurally with the Python 3 standard
library only (a small scanline rasterizer: ellipses, polygons, Bezier
noodle strands, translucent steam) and encodes the PNG with `zlib`. No
external files, no network, no randomness beyond a fixed seed — run it
twice and the bytes are identical.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Writes `out/entry.png` (1024x1024, under 1 MiB). Without
`MAKEFUN_OUTPUT_DIR` it writes to `/output`, as the competition runs it.

## License

MIT — see [LICENSE](LICENSE).
