from typing import Literal
from utils import channels

__icons = {
    # tiers
    "Tier 0" : '<:tier0:1126268390605070426>',
    "Tier 1" : '<:tier1:1126268393725644810>',
    "Tier 2" : '<:tier2:1126268395483037776>',
    "Tier 3" : '<:tier3:1126268398561677364>',
    "Tier 4" : '<:tier4:1126268402596585524>',
    "Tier 5" : '<:tier5:1126268404781809756>',
    "Tier 6" : '<:tier6:1126268408116285541>',
    "Tier 7" : '<:tier7:1126268411220074547>',

    # categories
    "Action" : '<:CE_action:1126326215356198942>',
    "Arcade" : '<:CE_arcade:1126326209983291473>',
    "Bullet Hell" : '<:CE_bullethell:1126326205642190848>',
    "First-Person" : '<:CE_firstperson:1126326202102186034>',
    "Platformer" : '<:CE_platformer:1126326197983383604>',
    "Strategy" : '<:CE_strategy:1126326195915591690>',

    # others
    "Points" : '<:CE_points:1128420207329816597>',
    'Arrow' : '<:CE_arrow:1126293045315375257>',

    # ranks
    "A Rank" : '<:rank_a:1126268299504795658>',
    "B Rank" : '<:rank_b:1126268303480979517>',
    "C Rank" : '<:rank_c:1126268305083215913>',
    "D Rank" : '<:rank_d:1126268307813715999>',
    "E Rank" : '<:rank_e:1126268309730512947>',
    "S Rank" : '<:rank_s:1126268319855562853>',
    "SS Rank" : '<:rank_ss:1126268323089367200>',
    "SSS Rank" : '<:rank_sss:1126268324804833280>',
    "EX Rank" : '<:rank_ex:1126268312842666075>',
    "P Rank" : '<:rank_p:1126268315279564800>',
    "Q Rank" : '<:rank_q:1126268318081364128>',

    # miscellaneous
    "Casino" : '<:CE_casino:1128844342732263464>',
    "Diamond" : '<:CE_diamond:1126286987524051064>',
    "All" : '<:CE_all:1126326219332399134>',
    "Rank Omega" : '<:rank_omega:1126293063455756318>',
    "Hexagon" : '<:CE_hexagon:1126289532497694730>',
    "Site Dev" : '<:SiteDev:963835646538027018>',

    # reactions
    "Shake" : '<:shake:894912425869074462>',
    "Safety" : '<:safety:802615322858487838>',
    "Crown" : "<:crown:1289287905331777596>",

    # logos
    "steam" : '<:steam:1282856420827463730>',
    "retroachievements": "<:retroachievementslogo:1282856386228916285>"
}


__test_icons = {
    "Action" : "<:CE_action:1133558549990088734>",
    "Arcade" : "<:CE_arcade:1133558574287683635>",
    "Bullet Hell" : "<:CE_bullethell:1133558610530676757>",
    "First-Person" : "<:CE_firstperson:1133558611898015855>",
    "Platformer" : "<:CE_platformer:1133558613705769020>",
    "Points" : "<:CE_points:1133558614867587162>",
    "Strategy" : "<:CE_strategy:1133558616536915988>",

    "Tier 0" : "<:tier0:1133560874464985139>",
    "Tier 1" : "<:tier1:1133560876381773846>",
    "Tier 2" : "<:tier2:1133560878294372432>",
    "Tier 3" : "<:tier3:1133560879544291469>",
    "Tier 4" : "<:tier4:1133560881356226650>",
    "Tier 5" : "<:tier5:1133560882291548323>",
    "Tier 6" : "<:tier6:1133540654983688324>",
    "Tier 7" : "<:tier7:1133540655981920347>",
    
    "Crown" : "<:crown:1289290399025860691>",
}

__ICON_KEYS = Literal['Tier 0', 'Tier 1', 'Tier 2', 'Tier 3', 
             'Tier 4', 'Tier 5', 'Tier 6', 'Tier 7', 
             'Action', 'Arcade', 'Bullet Hell', 'First-Person', 
             'Platformer', 'Strategy', 'Points', 'Arrow', 
             'A Rank', 'B Rank', 'C Rank', 'D Rank', 'E Rank', 
             'S Rank', 'SS Rank', 'SSS Rank', 'EX Rank', 'P Rank', 
             'Q Rank', 'Casino', 'Diamond', 'All', 'Rank Omega', 
             'Hexagon', 'Site Dev', 'Shake', 'Safety', 'steam',
             'retroachievements', 'Crown']

def get_emoji(input : __ICON_KEYS) -> str :
    """
    Returns the emoji related to `input`.
    """
    if not channels.IN_CE and input in __test_icons :
        return __test_icons[input]
    return __icons.get(input, "bad-input")


# ------------- image icons -------------
CE_MOUNTAIN_ICON = "https://i.imgur.com/4PPsX4o.jpg"
"""The mountain icon used most commonly by CE."""
CE_HEX_ICON = "https://i.imgur.com/FLq0rFQ.png"
"""The hex icon used by CE's banner."""
CE_JAMES_ICON = "https://i.imgur.com/fcdHTvx.png"
"""The icon made by James that was previously used."""
FINAL_CE_ICON = "https://i.imgur.com/O9J7fg2.png"
"""The icon made by @crappy for CE Assistant."""