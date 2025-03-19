# Luna Kit
This is a toolkit that is used for reading files from the My Little Pony Magic Princess Gameloft game.

# Installation
You can install Luna Kit by first making sure [python](https://python.org), and [git](https://git-scm.com/) is installed, then run

```shell
pip install git+https://github.com/ego-lay-atman-bay/luna-kit
```

To update, run this command.

```shell
pip install --upgrade git+https://github.com/ego-lay-atman-bay/luna-kit --force
```

# Usage

You can use Luna Kit by running

```shell
luna-kit -h
```

If that doesn't work, use `python -m luna_kit` instead of `luna-kit` (if you're on windows, you can use `py` instead of `python`).

## Extracting `.ark` files

Extract `.ark` files with this command

```shell
luna-kit ark "path/to/ark.ark" -o "output/folder"
```

This also accepts multiple `.ark` files.

```shell
luna-kit ark "path/to/ark.ark" "another_ark.ark" -o "output"
```

The filename can also be a glob pattern (selects all the `.ark` files in a folder).

```shell
luna-kit ark "path/to/*.ark" -o "output"
```

## Split `.texatlas` files

You can split `.texatlas` files using this command.

```shell
luna-kit atlas path/to/file.texatlas -o output
```

You can leave `-o output` off to get the images in the location that they are in the game.

## Convert `.loc` files to json

`.loc` files are localization files that contain every string used in the game in each language. These can be converted to a json file just by running

```shell
luna-kit loc "english.loc"
```

And this will save `english.json`.

You can also output csv files

```shell
luna-kit loc "english.loc" --format csv
```

# Converting audio

The audio files are stored in `mpc` files. They can be converted to `wav` using ffmpeg, however the quality is not very good. To get the best quality conversion, use the official Musepack `mpcdec` command line utility, which is actually what the game uses. It can be downloaded at https://www.musepack.net/.

There are also some `vxn` files, which are files that contain multiple audio streams. You can use [vxn-py](https://github.com/ego-lay-atman-bay/vxn-py) to extract all the audio streams to audio files.

# Credits
- I got the information about v1 ark files from [Pony3Ark](https://github.com/Arzaroth/Pon3Ark).
- Most of the code to read v3 ark files is based off of [Celestia's ARK](https://gist.github.com/liamwhite/ba39ce769424b53a5505).

The major inspiration for creating this, was to eliminate the compilation step in Celestia's ARK, as well as providing an easy to use api. I called this "Luna Kit", because it's a toolkit for reading (and writing some) files inside My Little Pony Magic Princess, including `.ark` files, splitting `.texatlas` files, converting `.loc` files to json, etc.
