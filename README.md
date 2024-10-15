# Luna Kit
This is a toolkit that is used for reading files from the My Little Pony Magic Princess Gameloft game. Currently it can only extract `.ark` files, but later may add more functionality.

# Usage
You can install Luna Kit by first making sure [python](https://python.org) is installed, then run.

```
pip install git+https://github.com/ego-lay-atman-bay/luna-kit
```

You can then use Luna Kit by using

```
python -m luna_kit -h
```

## Extracting `.ark` files

Extract `.ark` files with this command

```
python -m luna_kit ark "path/to/ark.ark" -o "output/folder"
```

This also accepts multiple `.ark` files.

```
python -m luna_kit ark "path/to/ark.ark" "another_ark.ark" -o "output"
```

# Credits
This project is based off of [Celestia's Ark](https://gist.github.com/liamwhite/ba39ce769424b53a5505), in fact, a lot of the `.ark` file reading code was taken from Celestia's Ark (just rewritten in python).

The major inspiration for creating this, was to eliminate the compile step in Celestia's Ark, as well as providing an easy to use api. I called this "Luna Kit", because I'm planning on doing more than just extracting `.ark` file (maybe writing to them?).

## Split `.texatlas` files

You can split `.texatlas` files using

```
python -m luna_kit atlas path/to/file.texatlas -o output
```
