from dataclasses import dataclass, field
from .SLMessages import IDs

import logging

log = logging.getLogger(__name__)

import configparser


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
    sourceType: str

    def summary(self):
        """Return key attributes as string"""
        return f"Unknown source type"

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
            len(self.sourceType) > 0
            and self.sourceType[0].isalpha()
            and self.sourceType.isalnum()
        ):
            OK = False
            errors.extend(
                [
                    f"Invalid type ('{self.sourceType}'). Source type must be alphanumeric (without spaces) and start with a letter."
                ]
            )

        return OK, errors


@dataclass
class SLCUnknown(SLCSource):
    tag: str
    sourceType: str
    params: list = field(default_factory=list)

    def summary(self):
        r = "Unknown source type"
        if len(self.params) > 0 and len("".join(self.params)) > 0:
            r += ". Parameters: " + ", ".join([x.strip() for x in self.params])
        return r

    def validate(self):
        OK, errors = super().validate()
        return (OK, errors)


@dataclass
class SLCSerial(SLCSource):
    name: str = None
    port: str = None
    baud: int = 115200
    sourceType: str = "SERIAL"
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
    sourceType: str = "NET"
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
    sourceType: str = "SL"

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


def SLCAuto(sourceType):

    typeMap = {"SERIAL": SLCSerial, "MP": SLCMP, "SL": SLCMP}

    return typeMap.get(sourceType.upper(), SLCUnknown)
