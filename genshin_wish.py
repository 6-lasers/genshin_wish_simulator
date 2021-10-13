#!/usr/bin/env python
######################################################
#
#    genshin_wish.py
#
#  Simulator for pulls in Genshin Impact
#
#  Usage: genshin_wish.py [-h] [-c <number>] [-p <x:y,...>] [-d] [-nc] <banner name>
#
######################################################

from __future__ import print_function

import sys
import argparse
import random
import json

# Loading raw banner and pool data from JSON
with open("event_banners.json", "r") as f:
    event_wish_list = json.load(f)
with open("std_pools.json", "r") as f:
    pools = json.load(f)
    std_3_star_pool = pools['std_3_star_pool']
    starter_char_pool = pools['starter_char_pool']
    std_4_char_pool = pools['std_4_char_pool']
    std_4_weap_pool = pools['std_4_weap_pool']
    std_5_char_pool = pools['std_5_char_pool']
    std_5_weap_pool = pools['std_5_weap_pool']

# Following odds and pity limits from:
# https://www.hoyolab.com/article/497840
# Secondary pity:
# 270 pulls 5* weapon and char
# 30 pulls 4* weapon and char

base_odds = {
    'standard': {
        '4': 0.051,
        '5': 0.006
    },
    'weapon': {
        '4': 0.06,
        '5': 0.007
    }
}

pity_limit = {
    'standard': {
        '4': 9,
        '5': 74
    },
    'weapon': {
        '4': 8,
        '5': 63
    }
}

# Calculate odds for pool based on current pity count
def get_odds(banner_type, pool, pity, debug=False):
    odds = base_odds[banner_type][pool]
    if pity[pool] >= pity_limit[banner_type][pool]:
        odds += (1 + pity[pool] - pity_limit[banner_type][pool]) * base_odds[banner_type][pool] * 10
    if debug:
        print("{0}* pity: {1}, {2:.1%} chance".format(pool, pity[pool], odds))
    return odds

# Pick pools in order of priority
def pick_pool(banner_type, pity, debug=False):
    if debug:
        print("Pulling {0}, pity is {1}/{2}".format(banner_type, pity['4'], pity['5']))
    # Test 5*
    odds = get_odds(banner_type, '5', pity, debug)
    if random.random() < odds:
        return '5'
    
    # Test 4*
    odds = get_odds(banner_type, '4', pity, debug)
    if random.random() < odds:
        return '4'
    
    return '3'

class bannerState:
    pity = {}
    pull_type = ""
    banner = {}
    do_pull = None
    debug = False
    
    # Standard pull with no guarantees
    # or featured items
    def do_standard_pull(self):
        self.pity['4'] += 1
        self.pity['5'] += 1
        
        pool = pick_pool("standard", self.pity, self.debug)
        if pool == '3':
            item = random.choice(self.banner['drops'][pool])
        else:
            self.pity[pool] = 0
            # TODO secondary pity
            item = random.choice(self.banner['drops'][pool]['character'] + self.banner['drops'][pool]['weapon'])
        
        return pool,item
    
    # Event pulls with 50/50 guarantees
    def do_event_pull(self):
        self.pity['4'] += 1
        self.pity['5'] += 1
        
        pool = pick_pool(self.pull_type, self.pity, self.debug)
        if pool == '3':
            item = random.choice(self.banner['drops'][pool])
        else:
            self.pity[pool] = 0
            if pool == '4':
                # 50/50 + guarantee
                if self.debug:
                    print("Pull 4*, guaranteed pity:", self.pity['4g'])
                if self.pity['4g'] or random.choice([True, False]):
                    self.pity['4g'] = 0
                    item = random.choice(self.banner['drops'][pool]['featured'])
                else:
                    self.pity['4g'] = 1
                    # TODO secondary pity
                    item = random.choice(self.banner['drops'][pool]['other_char'] + self.banner['drops'][pool]['other_weapon'])
            else:
                # 50/50 + guarantee
                if self.debug:
                    print("Pull 5*, guaranteed pity:", self.pity['5g'])
                if self.pity['5g'] or random.choice([True, False]):
                    self.pity['5g'] = 0
                    item = random.choice(self.banner['drops'][pool]['featured'])
                else:
                    self.pity['5g'] = 1
                    item = random.choice(self.banner['drops'][pool]['other'])
        
        return pool,item
    
    def __init__(self, banner, pity=None, debug=False):
        self.debug = debug
        
        # Initialize banner type
        if banner == "standard":
            self.pull_type = "standard"
            self.banner = banners[banner]
            self.do_pull = self.do_standard_pull
        else:
            self.do_pull = self.do_event_pull
            
            # Weapon vs character banner
            if banner[-5:] == "_weap":
                self.pull_type = "weapon"
                self.banner = banners['weapon']
            else:
                self.pull_type = "standard"
                self.banner = banners['character']
            # Distinguish featured items
            for pool in ['4', '5']:
                self.banner['drops'][pool]['featured'] = event_wish_list[banner][pool]
                # Banner featured item guarantee
                self.pity[pool + "g"] = 0
            # Remove featured items from 'other' category
            self.banner['drops']['4']['other_char'] = [item for item in self.banner['drops']['4']['other_char'] if item not in event_wish_list[banner]['4']]
            self.banner['drops']['4']['other_weapon'] = [item for item in self.banner['drops']['4']['other_weapon'] if item not in event_wish_list[banner]['4']]
            self.banner['drops']['5']['other'] = [item for item in self.banner['drops']['5']['other'] if item not in event_wish_list[banner]['5']]
            
            if self.debug:
                print("Banner: " + banner)
                print(json.dumps(self.banner, sys.stdout, indent=4))
        
        # Initialize pity
        self.pity.update({key: 0 for key in self.banner['drops']})
        
        # Load optional 'pity' argument
        if pity:
            for flag in pity.split(","):
                (key, value) = flag.split(":")
                if key in self.pity:
                    self.pity[key] = int(value)


# Base loadouts for banner types.
# Not JSON so we can use higher level logic
banners = {
    'standard': {
        'drops':
        {
            '3': std_3_star_pool,
            '4': {
                'character': std_4_char_pool + starter_char_pool,
                'weapon': std_4_weap_pool
            },
            '5': {
                'character': std_5_char_pool,
                'weapon': std_5_weap_pool
            }
        }
    },
    'character': {
        'drops':
        {
            '3': std_3_star_pool,
            '4': {
                'other_char': std_4_char_pool,
                'other_weapon': std_4_weap_pool
            },
            '5': {
                'other': std_5_char_pool
            }
        }
    },
    'weapon': {
        'drops':
        {
            '3': std_3_star_pool,
            '4': {
                'other_char': std_4_char_pool,
                'other_weapon': std_4_weap_pool
            },
            '5': {
                'other': std_5_weap_pool
            }
        }
    }
}

# No color for 3*
# ASCII purple for 4*
# ASCII yellow for 5*
pool_color = {
    '3': "",
    '4': '\033[35m',
    '5': '\033[33m'
}

def main(argv=None):
    parser = argparse.ArgumentParser(description="Simulator for pulls in Genshin Impact")
    parser.add_argument("banner", metavar="<banner name>", help="Name of the banner to simulate. Use \"list\" to list banner names.")
    parser.add_argument("-c", "--count", metavar="<number>", type=int, default=1, help="Number of pulls to simulate")
    parser.add_argument("-p", "--pity", metavar="<x:y,...>", help="Current pity count, in a comma-separated list of <pity type>:<pity count>")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable verbose output")
    parser.add_argument("-nc", "--nocolor", action="store_true", help="Remove ASCII color codes from output")
    
    args = parser.parse_args()
    
    if args.banner == "list":
        print("\n".join(["standard"] + event_wish_list.keys()))
        return 0
    
    myBanner = bannerState(args.banner, args.pity, args.debug)
    for i in range(args.count):
        result = myBanner.do_pull()
        if args.nocolor:
            print(result[1])
        else:
            print(pool_color[result[0]] + result[1] + "\033[0m")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

