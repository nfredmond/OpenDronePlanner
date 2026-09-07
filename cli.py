"""File-based local API for scripts and agents. No implicit USB writes."""
import argparse
import json
from pathlib import Path
from formats import import_file,export_kmz,export_split
from planner import generate,review

parser=argparse.ArgumentParser(description='OpenDronePlanner local file tools')
parser.add_argument('operation',choices=['import','generate','review','export','split'])
parser.add_argument('source',type=Path)
parser.add_argument('-o','--output',type=Path)
a=parser.parse_args()
try:
    if a.operation=='import':value=import_file(a.source.name,a.source.read_bytes())
    else:
        mission=json.loads(a.source.read_text())
        if a.operation=='generate':value=generate(mission)
        elif a.operation=='review':value=review(mission)
        elif a.operation=='export':value=export_kmz(mission)
        else:value=export_split(mission)
    if isinstance(value,bytes):
        if not a.output:parser.error('Binary export requires --output')
        a.output.write_bytes(value)
    elif a.output:a.output.write_text(json.dumps(value,indent=2)+'\n')
    else:print(json.dumps(value,indent=2))
except Exception as error:parser.exit(1,str(error)+'\n')
