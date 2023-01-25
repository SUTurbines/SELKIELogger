from dataclasses import dataclass, field, asdict
from .SLMessages import IDs

import logging

log = logging.getLogger(__name__)

import configparser

## See below for the main source type mapping and descriptions


class SLConfiguration:
    def __init__(self, **kwargs):
        self.frequency = int(kwargs.get("frequency", 10))
        self.savestate = self.getbool("savestate", kwargs, True)
        self.rotate = self.getbool("rotate", kwargs, True)
        self.statefile = kwargs.get("statefile", "logger.state")
        self.dataprefix = kwargs.get("prefix", "logger")
        self.verbose = int(kwargs.get("verbose", 1))
        self.sources = {}

    def tags(self):
        return self.sources.keys()

    def getSourceNumbers(self):
        sn = []
        for s in self.sources:
            try:
                sn.append(self.sources[s].sourcenum)
            except AttributeError:
                pass
        return sn

    def addSource(self, src):
        if src.tag in self.sources:
            raise KeyError("Cannot add source with existing tag value")

        try:
            sn = src.sourcenum

            # This won't detect clashes with dynamically numbered sources, but
            # will at least exclude statically configured problems

            if sn in self.getSourceNumbers():
                raise KeyError("Cannot add source with duplicate source number")

        except AttributeError:
            pass

        self.sources[src.tag] = src

    def removeSource(self, tag):
        if isinstance(tag, SLCSource):
            tag = tag.tag
        if not tag in self.sources:
            return
        del self.sources[tag]

    def updateSource(self, src):
        self.removeSource(src)
        self.addSource(src)

    def validate(self):
        OK = True
        errors = []

        if self.frequency <= 0:
            OK = False
            errors.extend("Core recording frequency must be greater than zero")

        if self.verbose < 0:
            OK = False
            errors.extend(["Core log verbosity must be greater than or equal to zero"])

        for s in self.sources:
            so, se = self.sources[s].validate()
            OK = OK and so
            errors.extend([f"{s}: {x}" for x in se])

        return OK, errors

    def save(self, fn):
        with open(fn, "w") as f:
            f.write(f"## SLConfig\n")
            f.write(f"frequency = {self.frequency}\n")
            f.write(f"savestate = {self.savestate}\n")
            f.write(f"rotate = {self.rotate}\n")
            f.write(f"statefile = {self.statefile}\n")
            f.write(f"prefix = {self.dataprefix}\n")
            f.write(f"verbose = {self.verbose}\n")

            sd = {}
            for stag in self.sources:
                src = self.sources[stag].dict()
                if "tag" in src:
                    del src["tag"]
                sd[stag] = src

            c = configparser.ConfigParser()
            c.read_dict(sd)
            c.write(f)

    @staticmethod
    def read(fn):
        from itertools import chain

        slc = SLConfiguration()  # Create new instance with defaults

        c = configparser.ConfigParser(default_section=None)
        with open(fn, "r") as f:
            c.read_file(chain(("[_core_]",), f))

        core = c["_core_"]
        slc.frequency = core.getint("frequency", fallback=slc.frequency)
        slc.savestate = core.getboolean("savestate", fallback=slc.savestate)
        slc.rotate = core.getboolean("rotate", fallback=slc.rotate)
        slc.dataprefix = core.get("prefix", fallback=slc.dataprefix)
        slc.statefile = core.get("statefile", fallback=slc.statefile)
        slc.verbose = core.get("verbose", fallback=slc.verbose)

        for section in c:
            print(section)
            if section == "_core_" or section is None:
                continue
            if "type" in c[section]:
                c[section]["sourcetype"] = c[section]["type"]
                del c[section]["type"]
            c[section]["tag"] = section
            slc.sources[section] = SLCAuto(c[section]["sourcetype"]).create(
                **c[section]
            )
        return slc

    @staticmethod
    def getbool(field, d, default):
        if d.get(field, None) is None:
            return default
        value = d.get(field)
        if isinstance(value, bool):
            return value
        else:
            try:
                return configparser.ConfigParser.BOOLEAN_STATES[value]
            except KeyError:
                raise ValueError(
                    f"Unable to interpret {field} value '{value}' as boolean"
                ) from None


@dataclass
class SLCSource:
    """Represent configuration for a data source"""

    tag: str
    sourcetype: str

    def summary(self):
        """Return key attributes as string"""
        return f"Unknown source type"

    def dict(self):
        d = asdict(self)
        d["type"] = d["sourcetype"]
        del d["sourcetype"]
        return d

    @classmethod
    def create(cls, **kwargs):
        if "type" in kwargs:
            kwargs["sourcetype"] = kwargs["type"]
            del kwargs["type"]

        if "sourcenum" in kwargs:
            kwargs["sourcenum"] = int(kwargs["sourcenum"], 0)

        return cls(**kwargs)

    def validate(self):
        errors = []
        OK = True
        if not (len(self.tag) > 0 and self.tag[0].isalpha() and self.tag.isalnum()):
            errors.extend(
                [
                    f"Invalid tag ('{self.tag}'): Tag must be alphanumeric (without spaces) and start with a letter"
                ]
            )
            OK = False

        if not (
            len(self.sourcetype) > 0
            and self.sourcetype[0].isalpha()
            and self.sourcetype.isalnum()
        ):
            OK = False
            errors.extend(
                [
                    f"Invalid type ('{self.sourcetype}'). Source type must be alphanumeric (without spaces) and start with a letter."
                ]
            )

        return OK, errors


@dataclass
class SLCUnknown(SLCSource):
    tag: str
    sourcetype: str
    params: list = field(default_factory=list)

    def summary(self):
        r = "Unknown source type"
        if len(self.params) > 0 and len("".join(self.params)) > 0:
            r += ". Parameters: " + ", ".join([x.strip() for x in self.params])
        return r

    def dict(self):
        d = super().dict()
        del d["params"]
        for line in self.params:
            print(line)
            s = line.split("=")
            k = s[0].strip()
            v = " ".join(s[1:]).strip()
            if k in d:
                if isinstance(d[k], list):
                    d[k].extend([v])
                else:
                    d[k] = [d[k], v]
            else:
                d[k] = v

        return d

    @classmethod
    def create(cls, **kwargs):
        sourcetype = None
        tag = None
        if "type" in kwargs:
            sourcetype = kwargs["type"]
            del kwargs["type"]
        elif "sourcetype" in kwargs:
            sourcetype = kwargs["sourcetype"]
            del kwargs["sourcetype"]
        else:
            raise ValueError("Cannot create source without a type")

        if "tag" in kwargs:
            tag = kwargs["tag"]
            del kwargs["tag"]
        else:
            raise ValueError("Cannot create source without a tag")

        params = []
        for k, v in kwargs.items():
            if k in ["tag", "sourcetype"]:
                continue
            params.extend([f"{k} = {v}"])
        "\n".join(params)

        return cls(tag=tag, sourcetype=sourcetype, params=params)

    def validate(self):
        OK, errors = super().validate()
        return (OK, errors)


@dataclass
class SLCSerial(SLCSource):
    name: str = None
    port: str = None
    baud: int = 115200
    sourcetype: str = "SERIAL"
    sourcenum: int = None
    minbytes: int = 1
    maxbytes: int = 100
    frequency: int = 10

    def __post_init__(self):
        if self.name is None:
            self.name = self.tag
            log.warning(f"[{self.tag}] No name specified, '{self.name}' assigned")

        if self.sourcenum is None:
            self.sourcenum = IDs.SLSOURCE_EXT
            log.warning(
                f"[{self.tag}] No source number specified, {self.sourcenum} assigned"
            )

    def summary(self):
        return f"Name={self.name}, ID=0x{self.sourcenum:02x}: {self.port}@{self.baud}, {self.frequency}Hz"

    def validate(self):
        OK, errors = super().validate()

        if not (len(self.port) > 0):
            OK = False
            errors.extend([f"Path to port must be provided"])

        if not (self.baud > 0):
            OK = False
            errors.extend(
                [
                    f"Baud rate ({self.baud}) must be a positive number (and must also be supported by target hardware - not checked here)"
                ]
            )

        if not (self.minbytes > 0):
            OK = False
            errors.extend([f"Minimum recordable bytes must be greater than 0"])

        if not (self.maxbytes > 1):
            OK = False
            errors.extend(["Maximum recordable bytes must be greater than 1"])

        if self.maxbytes < self.minbytes:
            OK = False
            errors.extend(
                [
                    "Maximum recordable bytes ({self.maxbytes}) cannot be less than the minimum recordable bytes ({self.minbytes})"
                ]
            )

        if self.frequency < 0:
            OK = False
            errors.extend(["Frequency must be a number greater than zero"])

        return (OK, errors)


@dataclass
class SLCNet(SLCSource):
    name: str = None
    port: int = 9999
    host: str = None
    sourcetype: str = "NET"
    sourcenum: int = None
    minbytes: int = 1
    maxbytes: int = 100
    frequency: int = 10

    def __post_init__(self):
        if self.name is None:
            self.name = self.tag
            log.warning(f"[{self.tag}] No name specified, '{self.name}' assigned")

        if self.sourcenum is None:
            self.sourcenum = IDs.SLSOURCE_EXT
            log.warning(
                f"[{self.tag}] No source number specified, {self.sourcenum} assigned"
            )

    def summary(self):
        return f"Name={self.name}, ID=0x{self.sourcenum:02x}: TCP:{self.host}:{self.port}, {self.frequency}Hz"

    def validate(self):
        OK, errors = super().validate()

        if not (self.port > 0):
            OK = False
            errors.extend([f"Port number ({self.port}) must be greater than zero"])

        if not (len(self.host) > 0):
            OK = False
            errors.extend([f"Hostname must be provided"])

        if not (self.minbytes > 0):
            OK = False
            errors.extend([f"Minimum recordable bytes must be greater than 0"])

        if not (self.maxbytes > 1):
            OK = False
            errors.extend(["Maximum recordable bytes must be greater than 1"])

        if self.maxbytes < self.minbytes:
            OK = False
            errors.extend(
                [
                    "Maximum recordable bytes ({self.maxbytes}) cannot be less than the minimum recordable bytes ({self.minbytes})"
                ]
            )

        if self.frequency < 0:
            OK = False
            errors.extend(["Frequency must be a number greater than zero"])

        return (OK, errors)


@dataclass
class SLCMP(SLCSource):
    port: str = None
    baud: int = 115200
    sourcetype: str = "SL"

    def summary(self):
        return f"SL: {self.port}@{self.baud}"

    def validate(self):
        OK, errors = super().validate()

        if not (len(self.port) > 0):
            OK = False
            errors.extend([f"Path to port must be provided"])

        if not (self.baud > 0):
            OK = False
            errors.extend(
                [
                    f"Baud rate ({self.baud}) must be a positive number (and must also be supported by target hardware - not checked here)"
                ]
            )

        return OK, errors


@dataclass
class SLCDW(SLCSource):
    name: str = None
    host: str = None
    sourcetype: str = "DW"
    sourcenum: int = None
    timeout: int = 180
    raw: bool = False
    spectrum: bool = False

    def __post_init__(self):
        if self.name is None:
            self.name = self.tag
            log.warning(f"[{self.tag}] No name specified, '{self.name}' assigned")

        if self.sourcenum is None:
            self.sourcenum = IDs.SLSOURCE_EXT
            log.warning(
                f"[{self.tag}] No source number specified, {self.sourcenum} assigned"
            )

    def summary(self):
        extras = []
        if self.spectrum:
            extras.extend(["Spectrum"])

        if self.raw:
            extras.extend(["Raw data"])

        if len(extras) > 0:
            extras = "[" + ", ".join(extras) + "]"
        else:
            extras = ""
        return f"Name={self.name}, ID=0x{self.sourcenum:02x}: {self.host} {extras}"

    def validate(self):
        OK, errors = super().validate()

        if not (len(self.host) > 0):
            OK = False
            errors.extend([f"Hostname must be provided"])

        return (OK, errors)


SourceTypes = {
    # TYPE: Class, Description, Show by default
    # TYPE must match that in logger/LoggerDMap.c
    "DW": (SLCDW, "Datawell wave buoy receiver support", True),
    "GPS": (SLCUnknown, "uBlox GPS module (or compatible)", True),
    "I2C": (SLCUnknown, "I2C connected sensors", True),
    "NMEA": (SLCUnknown, "Classic NMEA serial interface", True),
    "N2K": (SLCUnknown, "Actisense NMEA 2000 gateway (or compatible)", True),
    "MP": (SLCMP, "SELKIELogger compatible hardware", False),
    "SL": (SLCMP, "SELKIELogger compatible hardware", True),
    "SERIAL": (SLCSerial, "Generic serial device support (record only)", True),
    "TCP": (SLCNet, "Generic network stream (record only)", False),
    "NET": (SLCNet, "Generic network stream (record only)", True),
    "TIMER": (SLCUnknown, "Software defined timestamp generator", False),
    "TICK": (SLCUnknown, "Software defined timestamp generator", False),
    "LPMS": (SLCUnknown, "LP Research IMU devices", True),
    "MQTT": (
        SLCUnknown,
        "Subscribe to MQTT network broker (includes Victron devices)",
        True,
    ),
}


def SLCAuto(sourcetype):
    ST = SourceTypes.get(sourcetype.upper(), None)
    if ST:
        return ST[0]
    return SLCUnknown
