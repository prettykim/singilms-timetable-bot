import discord
from discord.ext import commands

from datetime import date, timedelta

from comcigan import School

from base64 import b64encode
from json import loads
from typing import List, Tuple

from requests import get
from bs4 import BeautifulSoup

from comcigan.reg import (
    routereg,
    prefixreg,
    orgdatareg,
    daydatareg,
    thnamereg,
    sbnamereg,
    regsearch,
    extractint,
)


def trim(lis):
    while lis and not lis[-1]:
        del lis[-1]
    return lis


URL = "http://112.186.146.81:4082"

comci_resp = get(f"{URL}/st")
comci_resp.encoding = "EUC-KR"

comcigan_html = BeautifulSoup(comci_resp.text, "lxml")
script = comcigan_html.find_all("script")[1].contents[0]

route = regsearch(routereg, script)
PREFIX = regsearch(prefixreg, script)[1:-1]

orgnum = extractint(regsearch(orgdatareg, script))
daynum = extractint(regsearch(daydatareg, script))
thnum = extractint(regsearch(thnamereg, script))
sbnum = extractint(regsearch(sbnamereg, script))

BASEURL = f"{URL}{route[1:8]}"
SEARCHURL = f"{BASEURL}{route[8:]}"


class SchoolEdited(School):
    __slots__ = ("name", "sccode", "_timeurl", "_week_data")

    name: str
    sccode: int
    _timeurl: str
    _week_data: List[List[List[List[Tuple[str, str, str]]]]]

    def __init__(self, name: str):
        sc_search = get(
            SEARCHURL
            + "%".join(
                str(name.encode("EUC-KR"))
                .upper()[2:-1]
                .replace("\\X", "\\")
                .split("\\")
            )
        )
        sc_search.encoding = "UTF-8"
        sc_list = loads(sc_search.text.replace("\0", ""))["학교검색"]

        if len(sc_list):
            self.name = sc_list[0][2]
            self.sccode = sc_list[0][3]
        else:
            raise NameError("No schools have been searched by the name passed.")

        self._timeurl = f"{BASEURL}?" + b64encode(
            f"{PREFIX}{str(self.sccode)}_0_1".encode("UTF-8")
        ).decode("UTF-8")
        self._week_data = [[[[("", "", "")]]]]
        self.refresh()

    def refresh(self):
        time_res = get(self._timeurl)
        time_res.encoding = "UTF-8"
        rawtimetable = loads(time_res.text.replace("\0", ""))

        subjects: list = rawtimetable[f"자료{sbnum}"]
        long_subjects: list = rawtimetable[f"긴자료{sbnum}"]
        teachers: list = rawtimetable[f"자료{thnum}"]

        self._week_data = [
            [
                [
                    [
                        (
                            subjects[int(str(x)[-2:])],
                            long_subjects[int(str(x)[-2:])],
                            ""
                            if int(str(x)[:-2]) >= len(teachers)
                            else teachers[int(str(x)[:-2])],
                        )
                        for x in filter(lambda x: str(x)[:-2], trim(oneday[1:]))
                    ]
                    for oneday in oneclass[1:6]
                ]
                for oneclass in onegrade
            ]
            for onegrade in rawtimetable[f"자료{daynum}"][1:]
        ]


singil = commands.Bot(command_prefix="!")
singil.remove_command("help")

day = date.today().day
wday = date.today().weekday()
nday = (date.today() + timedelta(days=1)).day
nwday = (date.today() + timedelta(days=1)).weekday()

myschool = SchoolEdited("신길중학교")
exist_zoom = {}

with open("link.txt", "r", encoding="utf8") as f:
    link = f.readlines()[2:]

    for i in link:
        if not i == "\n":
            exist_zoom[i.split()[0]] = i.split()[1]


@singil.event
async def on_ready():
    await singil.change_presence(status=discord.Status.online, activity=None)

    print(f"다음으로 로그인합니다: {singil.user.name}")


@singil.event
async def on_command_error(ctx, err):
    erembed = discord.Embed(
        title="죄송해요. 잘 이해하지 못했어요.",
        description="입력하신 명령어가 올바른지 확인해 주세요.",
        color=discord.Color.blue(),
    )

    await ctx.send(embed=erembed)

    print(f"{ctx.author.display_name}님이 알 수 없는 명령어를 입력하셨어요.")


@singil.command()
async def 오늘시간표(ctx):
    ttdescription = ""

    if wday == 5:
        tttitle = f"오늘({day}일)은 토요일이에요!"
        ttdescription = "학교 가시려고요?"
    elif wday == 6:
        tttitle = f"오늘({day}일)은 일요일이에요!"
        ttdescription = "학교 가시려고요?"
    else:
        tttitle = f"오늘({day}일) 시간표"

    if ttdescription:
        ttembed = discord.Embed(
            title=tttitle, description=ttdescription, color=discord.Color.blue()
        )
    else:
        ttembed = discord.Embed(title=tttitle, color=discord.Color.blue())

    if wday < 5:
        for i in range(len(myschool[1][2][wday])):
            ttclass = myschool[1][2][wday][i][0]

            if ttclass in exist_zoom:
                ttembed.add_field(
                    name=f"{i + 1}교시",
                    value=f"{ttclass}[(줌 링크)](<{exist_zoom[ttclass]}>)",
                    inline=False,
                )
            else:
                ttembed.add_field(name=f"{i + 1}교시", value=f"{ttclass}", inline=False)

    await ctx.send(embed=ttembed)

    print(f"{ctx.author.display_name}님이 '!오늘시간표'를 입력하셨어요.")


@singil.command()
async def 내일시간표(ctx):
    ttdescription = ""

    if nwday == 5:
        tttitle = f"내일({nday}일)은 토요일이에요!"
        ttdescription = "학교 가시려고요?"
    elif nwday == 6:
        tttitle = f"내일({nday}일)은 일요일이에요!"
        ttdescription = "학교 가시려고요?"
    else:
        tttitle = f"내일({nday}일) 시간표"

    if ttdescription:
        ttembed = discord.Embed(
            title=tttitle, description=ttdescription, color=discord.Color.blue()
        )
    else:
        ttembed = discord.Embed(title=tttitle, color=discord.Color.blue())

    if nwday < 5:
        for i in range(len(myschool[1][2][nwday])):
            ttclass = myschool[1][2][nwday][i][0]

            if ttclass in exist_zoom:
                ttembed.add_field(
                    name=f"{i + 1}교시",
                    value=f"{ttclass}[(줌 링크)](<{exist_zoom[ttclass]}>)",
                    inline=False,
                )
            else:
                ttembed.add_field(name=f"{i + 1}교시", value=f"{ttclass}", inline=False)

    await ctx.send(embed=ttembed)

    print(f"{ctx.author.display_name}님이 '!내일시간표'를 입력하셨어요.")


@singil.command()
async def 핑(ctx):
    pnembed = discord.Embed(
        title="퐁! 탁구공이 도착했어요.",
        description=f"현재 핑은 {round(singil.latency * 1000)}ms입니다.",
        color=discord.Color.blue(),
    )

    await ctx.send(embed=pnembed)

    print(f"{ctx.author.display_name}님이 '!핑'을 입력하셨어요.")


@singil.command()
async def 도움말(ctx):
    hpembed = discord.Embed(
        title="안녕하세요!",
        description="""자세한 정보는 아래에서 보실 수 있어요.
좋은 하루 되세요!""",
        color=discord.Color.blue(),
    )

    hpembed.add_field(
        name="명령어", value="`!오늘시간표`, `!내일시간표`, `!핑`, `!도움말`", inline=False
    )
    hpembed.add_field(name="제작자", value="HolyDiamonds7#3045", inline=False)
    hpembed.add_field(name="문의하기", value="mg7441081@gmail.com", inline=False)

    await ctx.send(embed=hpembed)

    print(f"{ctx.author.display_name}님이 '!도움말'을 입력하셨어요.")


with open("token.txt", "r") as f:
    singil.run(f"{f.read()}")
