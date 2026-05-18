import pandas as pd
import json

def format_number(n):
    """Format number with spaces every 3 digits"""
    return f"{n:,}".replace(",", " ")

def print_aligned(start, end, cost):
    """Print with support for 10s of millions"""
    print(f"Epic Start at {start:>3} → {end:<3}: {cost:>15,}")

def get_cost(costs, rarity, level, resource_type='xp'):
    """
    Get the cost of upgrading a character or item based on rarity, target level (levels in steps of 50), and resource type from the 'costs' dictionary

    costs         : the dictionary of costs, stored in level_costs.json
    rarity        : One of 'Common', 'Rare', 'Epic', 'Legendary' or 'Mythic'
    level         : One of  250, 300, 350 ... 700, 750 (steps of 50)
    resource_type : 'xp' or 'gems'
    """
    return costs[rarity][resource_type].get(level)

def sum_xp_from_start(costs, rarity, start_level = 0, end_level = 750):
    """
    Calculate total XP from start_level to end_level (levels in steps of 50).

    costs       : the dictionary of costs, stored in level_costs.json
    rarity      : One of 'Common', 'Rare', 'Epic', 'Legendary' or 'Mythic'
    start_level : Starting level. Default to 0
    end_level   : Ending level. Default to 750
    """
    if start_level >= end_level:
        return 0
    
    total = 0
    level = start_level
    while level < end_level:
        next_level = level + 50
        if next_level > end_level:
            next_level = end_level
        xp_step = costs[rarity]['xp'].get(next_level, 0)
        total += xp_step
        level = next_level
    
    return total

def sum_gems_from_start(costs, rarity, start_level, end_level):
    """
    Calculate total gems from start_level to end_level (levels in steps of 50).

    costs       : the dictionary of costs, stored in level_costs.json
    rarity      : One of 'Common', 'Rare', 'Epic', 'Legendary' or 'Mythic'
    start_level : Starting level. Default to 0
    end_level   : Ending level. Default to 750
    """
    if start_level >= end_level:
        return 0
    
    total = 0
    level = start_level
    while level < end_level:
        next_level = level + 50
        if next_level > end_level:
            next_level = end_level
        gems_step = costs[rarity]['gems'].get(next_level, 0)
        total += gems_step
        level = next_level
    
    return total


def which_girls_for_cap(unlock_caps, target_cap, 
                        rarity_limits = {'Common': 2500, 'Rare': 78, 'Epic': 109, 'Legendary': 999999, 'Mythic': 999999}, # Change commons to 25 for MRPG
                        min_requirements = None):
    """
    Determine which girls to pick to reach a new lvl cap 'target_cap' based on the amount of girls available as described in 'rarity_limits'
    Using at least the amount of girls described in 'min_requirements'

    'Unlock_caps'      : df containing requirements to unlock a specific level cap. It has two columns :
        level_cap                : the new cap to unlock
        girls_needed_to_reach_it : the amount of girls that need to reach level_cap-50 to reach that cap
    'target_cap'       : new lvl cap the user is trying to unlock
    'rarity_limits'    : dict like {'Common': 25, 'Rare': 78, 'Epic': 109, 'Legendary': 999999, 'Mythic': 999999}
    'min_requirements' : dict like {'Mythic' : 1, 'Legendary': 6, 'Epic': 0}  (minimum girls to use from that rarity)

    Example
    --------
    >>> which_girls_for_cap(unlock_caps, 850, 
    ...                     {'Common': 25, 'Rare': 78, 'Epic': 109, 
    ...                      'Legendary': 999999, 'Mythic': 999999})
    {'Common': 25, 'Rare': 78, 'Epic': 17, 'Legendary': 0, 'Mythic': 0}
    """
    # Get required number of girls at target_cap
    required = unlock_caps[unlock_caps['level_cap'] == target_cap]['girls_needed_to_reach_it'].values[0]
    
    rarities = ['Common', 'Rare', 'Epic', 'Legendary', 'Mythic']
    
    result = {rarity: 0 for rarity in rarities}
    # Step 1: Apply minimum requirements (from highest rarity down to lowest)
    if min_requirements:
        for rarity in reversed(rarities):
            if rarity in min_requirements:
                min_needed = min_requirements[rarity]
                limit = rarity_limits.get(rarity, 999999)
                take = min(min_needed, limit)
                result[rarity] = take
                required -= take
                if required < 0:
                    # Reduce the last applied rarity
                    result[rarity] += required
                    required = 0
                    break
    
    # Step 2: Fill remaining with lowest rarity first (respecting limits)
    remaining = max(0, required)
    
    for rarity in rarities:
        if remaining <= 0:
            break
        
        limit = rarity_limits.get(rarity, 999999)
        current = result[rarity]
        max_can_take = limit - current
        
        take = min(max_can_take, remaining)
        result[rarity] += take
        remaining -= take
    
    if remaining > 0:
        print(f"⚠️ Warning: Not enough girls! Still need {remaining} more.")
        result['_missing'] = remaining
    result = {rarity: int(count) for rarity, count in result.items()}
    return result

def total_cumulative_cost_for_cap(costs, unlock_caps, target_cap, rarity_limits, min_requirements=None):
    """
    Calculate total XP and Gems to unlock target_cap from 0
    More specifically, the function determines the minimal cost to reach requirements as states by df_caps and min_requirements from 0

    costs              : the dictionary of costs, stored in level_costs.json
    'Unlock_caps'      : df containing requirements to unlock a specific level cap. It has two columns :
        level_cap                : the new cap to unlock
        girls_needed_to_reach_it : the amount of girls that need to reach level_cap-50 to reach that cap
    'target_cap'       : new lvl cap the user is trying to unlock
    'rarity_limits'    : dict like {'Common': 25, 'Rare': 78, 'Epic': 109, 'Legendary': 999999, 'Mythic': 999999}
    'min_requirements' : dict like {'Mythic' : 1, 'Legendary': 6, 'Epic': 0}  (minimum girls to use from that rarity)

    
    Will pick the girls in min_requirements first
    Then lower rarities until rarity_limits is reached
    """
    girls_allocation = which_girls_for_cap(unlock_caps, target_cap, rarity_limits, min_requirements)
    
    target_cap_minus = target_cap - 50 # to unlock the cap, the girls must reach the cap - 50
    total_xp = 0
    total_gems = 0
    
    for rarity, count in girls_allocation.items():
        if rarity in costs and count > 0:
            # Cumulative XP from level 0 to target_cap
            total_xp += count * sum_xp_from_start(costs, rarity, 0, target_cap_minus)
            # Cumulative Gems from level 0 to target_cap
            total_gems += count * sum_gems_from_start(costs, rarity, 0, target_cap_minus)
    
    return total_xp, total_gems, girls_allocation


def print_cumulative_summary(costs, unlock_caps, target_cap, rarity_limits, min_requirements=None):
    """
    Basically total_cumulative_cost_for_cap, but pretty and provides context
    """
    total_xp, total_gems, allocation = total_cumulative_cost_for_cap(costs, unlock_caps, target_cap, rarity_limits, min_requirements)
    
    required_girls = unlock_caps[unlock_caps['level_cap'] == target_cap]['girls_needed_to_reach_it'].values[0]
    
    print(f"\n{'='*60}")
    print(f"  To unlock level cap {target_cap}")
    print(f"   Need {required_girls} girls at level {target_cap-50}")
    print(f"{'='*60}")
    print(f"  Girl allocation (from level 0 to {target_cap-50}):")
    for rarity, count in allocation.items():
        if count > 0 and rarity not in ['_missing']:
            xp_per_girl = sum_xp_from_start(costs, rarity, 0, target_cap)
            gems_per_girl = sum_gems_from_start(costs, rarity, 0, target_cap)
            print(f"   • {rarity:10}: {count:3} girls  (XP: {format_number(xp_per_girl)} each, Gems: {gems_per_girl} each)")
    
    if '_missing' in allocation:
        print(f"   /!\ MISSING: {allocation['_missing']} more girls needed")
    
    print(f"\n  TOTAL Cumulative Cost to unlock lvl {target_cap} cap):")
    print(f"   • XP : {format_number(total_xp)}")
    print(f"   • Gems: {format_number(total_gems)}")
    print(f"{'='*60}\n")
    
    return total_xp, total_gems, allocation


def unlock_from_another_cap(costs, df_caps, from_cap, to_cap, rarity_limits, min_requirements=None):
    """
    """
    total_xp, total_gems, allocation = total_cumulative_cost_for_cap(costs, df_caps, to_cap, rarity_limits, min_requirements)
    total_xp2, total_gems2, allocation2 = total_cumulative_cost_for_cap(costs, df_caps, from_cap, rarity_limits, min_requirements)
    return (total_xp-total_xp2), (total_gems-total_gems2)


def print_unlock_from_another_cap(costs, df_caps, from_cap, to_cap, rarity_limits, min_requirements=None):
    """Pretty print the cost to unlock a new tier from a previous tier"""
    total_xp, total_gems, allocation = total_cumulative_cost_for_cap(costs, df_caps, to_cap, rarity_limits, min_requirements)
    total_xp2, total_gems2, allocation2 = total_cumulative_cost_for_cap(costs, df_caps, from_cap, rarity_limits, min_requirements)
    
    print(f"\n{'='*60}")
    print(f"🔓 UNLOCK TIER: {from_cap} → {to_cap}")
    print(f"{'='*60}")
    print(f"📈 Additional Resources Needed:")
    print(f"   • XP   : {format_number(total_xp-total_xp2)}")
    print(f"   • Gems : {format_number(total_gems-total_gems2)}")
    print(f"{'='*60}\n")
    
    return (total_xp-total_xp2), (total_gems-total_gems2)
