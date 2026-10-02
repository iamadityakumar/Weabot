import yaml
import glob
from pathlib import Path

intents = {
    'SOP-001': 'Severe precipitation, torrential rain, monsoons, and flash flooding affecting all outdoor activities and travel.',
    'SOP-002': 'Extreme heat, heat exhaustion, and sunstroke risk during high-intensity outdoor exercise and running.',
    'SOP-003': 'Moderate heat, high apparent temperature, and dehydration caution during outdoor exercise and cycling.',
    'SOP-004': 'High sustained wind and crosswind collision hazards for cycling, bicycles, scooters, and two-wheelers.',
    'SOP-005': 'Wet roads, low traction, and hydroplaning hazards during vehicle commuting, driving, and road transit.',
    'SOP-006': 'Dense fog, smog, and low visibility collision hazards for road travel, commuting, and highway driving.',
    'SOP-007': 'Sub-zero freezing temperatures, hypothermia, and frostbite risk for elderly individuals, young children, and vulnerable groups during walks or outdoor strolls.',
    'SOP-008': 'High to extreme midday UV radiation exposure and sunburn risk for toddlers, children, and infants at playgrounds and parks.',
    'SOP-009': 'Hot asphalt pavement thermal burns and heat stress hazards for dogs and pets during outdoor walks.',
    'SOP-010': 'Severe thunderstorms, lightning strikes, and active convective storm cells during open-field outdoor recreation and sports.',
    'SOP-011': 'Optimal pleasant weather criteria for family picnics, park outings, open-air barbecues, and social gatherings.',
    'SOP-012': 'Marginal, cloudy, breezy, or damp conditions requiring contingency planning for outdoor picnics and gatherings.',
    'SOP-013': 'Moderate UV radiation caution and protective sunscreen guidance for children playing outdoors at parks or playgrounds.'
}

root = Path(__file__).resolve().parent.parent
for f in sorted((root / 'sops').glob('*.yaml')):
    content = f.read_text(encoding='utf-8')
    data = yaml.safe_load(content)
    sop_id = data['id']
    if sop_id in intents and 'intent:' not in content:
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if line.startswith('title:'):
                new_lines.append(f'intent: "{intents[sop_id]}"')
        content = '\n'.join(new_lines) + '\n'
    if sop_id == 'SOP-011':
        content = content.replace('Enjoy the outing with', 'Plan the outing with')
    f.write_text(content, encoding='utf-8')

print('Successfully updated all SOPs!')
