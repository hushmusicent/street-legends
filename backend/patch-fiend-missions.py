#!/usr/bin/env python3
"""Fiend missions for Street Legends (backend).

User spec (2026-11-05 09:58 EST): "Use 🧟 icon for Fiend. I want
these to be a different kind of missions where you sell the 5 items you get
from the enemies for 25% more of the regular price. But each of these
missions ask for various amounts of the items, like 1 Fiend mission might
want 2oz of grass and 5oz of rock candy. And another mission might want 3oz
of Flake. Make 1000 different variations of these missions. Also take the
sell button off the 5 items. Only can sell to Fiends and other players.
Let the fiend missions show up around players periodically."

Undercover-cop rule (user, 2026-11-05 10:00 EST, corrected 10:02 EST):
at completion time there is a flat 10% chance the Fiend is an undercover
cop. On a cop outcome the requested items ARE deducted (confiscated) AND
the player is fined $1,000 cash (capped at current cash, never below $0),
with NO payout. The mission is consumed on EITHER outcome (one attempt per
Fiend per player). Cop status is hidden until the attempt.

What this patch does (run order: AFTER the Brown Sugar backend patch,
then Publish, then the Fiend frontend patch):
  1. A deterministic 1,000-variant catalog: variant id 0-999 maps to a
     unique bundle of 1-3 of the five items, 1-5 oz each. Enumeration:
     ids 0-24 = singles (5 items x 5 qty), 25-274 = pairs (10 pairs x
     5x5 qty), 275-999 = triples (first 725 of 1250 in lex order: the
     first 6 triples x 125 qty combos, last triple partial). Payout =
     sum(qty x fiend price). Pure function of the id; no DB catalog.
  2. GET /fiends/nearby — at most ONE Fiend at a time, enforced
     server-side. Mirrors generate_missions: expired fiends cleaned,
     an existing active one within 1000m is returned as-is (minus
     fiends this player already attempted); if none is active, a new
     one spawns only after the periodic interval since this player's
     last completed Fiend (300s, mirroring the monsters' "1 more every
     5 minutes" cadence). Random offset +-0.005 deg, 24h expiry,
     persisted in db.fiend_missions so refetches are stable.
  3. POST /fiends/{fiend_id}/complete — verifies the player holds every
     requested quantity (a failed check does NOT consume the attempt),
     rolls the flat 10% cop chance, consumes the attempt atomically
     (conditional update on attempted_by; a retry sees modified_count 0
     and is rejected with no second roll, fine, or payout), deducts the
     items on EITHER outcome, then pays the fiend payout (sale) or the
     $1,000 fine capped at current cash (cop). Response carries
     "outcome": "sold" | "cop" so the frontend shows the right message.
  4. SELL enforcement: the five dedicated sell endpoints
     (/players/{id}/<item>/sell) now reject with HTTP 400 directing the
     player to a Fiend, before any inventory/cash touch. The generic
     /players/{id}/inventory/{item_id}/sell endpoint rejects the five
     item ids the same way (it pays value//2 and pops the whole stacked
     entry, so it must not be usable for them either).
  NOTE on "other players": no player-to-player selling/trading exists
  anywhere in the code (searched trade/market/offer/listing — nothing),
  so after this patch the ONLY working sell path is Fiends. A trade
  feature would be a separate build.

Fiend prices (regular x1.25, all integers): Grass $125, Pills $250,
Rock Candy $375, Flake $500, Brown Sugar $625 per oz.

Run:  python3 backend/patch-fiend-missions.py
   or:  python3 backend/patch-fiend-missions.py /path/to/app
Idempotent: rerun prints ALREADY_APPLIED per part, files unchanged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
SERVER = ROOT / "backend" / "server.py"

FIEND_CODE = '''
# FIEND_MISSIONS: buy the five enemy-drop items at +25% over regular price.
# Variant catalog is deterministic: variant id 0-999 maps to a unique bundle
# (1-3 item types, 1-5 oz each). Payout = sum(qty x fiend price).
# Names: FIEND_NAMES holds 1000 distinct real first names (500 male / 500
# female, interleaved M/F, from SSA baby-names popularity). A Fiend is named
# FIEND_NAMES[variant_id], so the name is deterministic per variant and the
# same Fiend keeps its name across refetches.
FIEND_ITEM_PRICES = {
    "grass": ("Grass", 100, 125),
    "pills": ("Pills", 200, 250),
    "rock_candy": ("Rock Candy", 300, 375),
    "flake": ("Flake", 400, 500),
    "brown_sugar": ("Brown Sugar", 500, 625),
}
FIEND_ITEM_IDS = ["grass", "pills", "rock_candy", "flake", "brown_sugar"]
FIEND_NAMES = [
    'John', 'Mary', 'James', 'Elizabeth', 'William', 'Margaret', 'Robert', 'Helen', 'Charles', 'Anna',
    'Michael', 'Dorothy', 'Joseph', 'Barbara', 'David', 'Patricia', 'George', 'Ruth', 'Thomas', 'Linda',
    'Richard', 'Jennifer', 'Edward', 'Betty', 'Frank', 'Sarah', 'Daniel', 'Alice', 'Paul', 'Nancy',
    'Donald', 'Susan', 'Christopher', 'Frances', 'Henry', 'Laura', 'Walter', 'Marie', 'Kenneth', 'Emma',
    'Anthony', 'Martha', 'Matthew', 'Catherine', 'Harry', 'Florence', 'Andrew', 'Rose', 'Arthur', 'Virginia',
    'Mark', 'Grace', 'Raymond', 'Jessica', 'Albert', 'Mildred', 'Ronald', 'Karen', 'Steven', 'Lillian',
    'Brian', 'Annie', 'Harold', 'Carol', 'Fred', 'Ethel', 'Samuel', 'Lisa', 'Willie', 'Shirley',
    'Kevin', 'Sandra', 'Joshua', 'Donna', 'Timothy', 'Katherine', 'Jack', 'Edna', 'Jason', 'Clara',
    'Carl', 'Amanda', 'Stephen', 'Evelyn', 'Joe', 'Emily', 'Gary', 'Rebecca', 'Jeffrey', 'Louise',
    'Clarence', 'Kimberly', 'Louis', 'Kathleen', 'Roy', 'Michelle', 'Larry', 'Bertha', 'Ralph', 'Julia',
    'Nicholas', 'Melissa', 'Eric', 'Sharon', 'Jacob', 'Amy', 'Benjamin', 'Ashley', 'Peter', 'Irene',
    'Ryan', 'Minnie', 'Lawrence', 'Edith', 'Scott', 'Stephanie', 'Jerry', 'Doris', 'Patrick', 'Ida',
    'Howard', 'Deborah', 'Ernest', 'Cynthia', 'Earl', 'Bessie', 'Jonathan', 'Angela', 'Eugene', 'Ann',
    'Justin', 'Josephine', 'Dennis', 'Carolyn', 'Gregory', 'Jean', 'Jesse', 'Christine', 'Brandon', 'Janet',
    'Douglas', 'Gladys', 'Francis', 'Joan', 'Gerald', 'Gertrude', 'Alexander', 'Joyce', 'Alfred', 'Ruby',
    'Herbert', 'Hazel', 'Jose', 'Ella', 'Aaron', 'Rachel', 'Leonard', 'Carrie', 'Adam', 'Eva',
    'Russell', 'Kathryn', 'Roger', 'Maria', 'Charlie', 'Brenda', 'Stanley', 'Mabel', 'Frederick', 'Pamela',
    'Nathan', 'Nellie', 'Philip', 'Pearl', 'Billy', 'Esther', 'Martin', 'Nicole', 'Tyler', 'Theresa',
    'Lee', 'Lois', 'Edwin', 'Judith', 'Norman', 'Heather', 'Keith', 'Diane', 'Wayne', 'Myrtle',
    'Oscar', 'Jane', 'Zachary', 'Elsie', 'Bruce', 'Julie', 'Elmer', 'Debra', 'Terry', 'Sara',
    'Theodore', 'Gloria', 'Kyle', 'Christina', 'Leo', 'Agnes', 'Ray', 'Lillie', 'Jeremy', 'Eleanor',
    'Victor', 'Samantha', 'Vincent', 'Ellen', 'Leroy', 'Anne', 'Allen', 'Victoria', 'Melvin', 'Pauline',
    'Sam', 'Marilyn', 'Bernard', 'Janice', 'Marvin', 'Beverly', 'Herman', 'Marjorie', 'Floyd', 'Thelma',
    'Sean', 'Mattie', 'Bobby', 'Lucille', 'Lewis', 'Phyllis', 'Clifford', 'Teresa', 'Phillip', 'Charlotte',
    'Clyde', 'Jacqueline', 'Glenn', 'Cora', 'Austin', 'Cheryl', 'Eddie', 'Beatrice', 'Johnny', 'Lucy',
    'Bryan', 'Lena', 'Alan', 'Jennie', 'Dale', 'Judy', 'Juan', 'Alma', 'Curtis', 'Hannah',
    'Lloyd', 'Norma', 'Jimmy', 'Lauren', 'Christian', 'Andrea', 'Tom', 'Megan', 'Chester', 'Bonnie',
    'Jim', 'Hattie', 'Alex', 'Rosa', 'Lester', 'Viola', 'Edgar', 'Stella', 'Randy', 'Rita',
    'Leon', 'Sylvia', 'Steve', 'Peggy', 'Warren', 'Bernice', 'Craig', 'Denise', 'Harvey', 'Diana',
    'Shawn', 'Mae', 'Travis', 'Wanda', 'Tony', 'Amber', 'Jordan', 'Danielle', 'Alvin', 'Katie',
    'Bradley', 'Blanche', 'Claude', 'Lula', 'Danny', 'Ada', 'Todd', 'Lori', 'Isaac', 'Tammy',
    'Wesley', 'Brittany', 'Joel', 'Crystal', 'Carlos', 'Fannie', 'Nathaniel', 'Tiffany', 'Calvin', 'Dora',
    'Mike', 'Elaine', 'Rodney', 'Kathy', 'Vernon', 'Dolores', 'Will', 'Maggie', 'Milton', 'Maude',
    'Bill', 'Juanita', 'Gordon', 'Geraldine', 'Manuel', 'Caroline', 'Jessie', 'Nora', 'Antonio', 'Daisy',
    'Cody', 'Mamie', 'Dylan', 'Audrey', 'Ben', 'Tina', 'Chad', 'Georgia', 'Don', 'Erin',
    'Ethan', 'Vera', 'Jay', 'Dawn', 'Cecil', 'Paula', 'Gabriel', 'Connie', 'Noah', 'Sally',
    'Luis', 'Natalie', 'Leslie', 'Olivia', 'Troy', 'Loretta', 'Maurice', 'Vivian', 'Gilbert', 'Lorraine',
    'Marcus', 'Kayla', 'Jerome', 'Robin', 'Jeffery', 'June', 'Franklin', 'Anita', 'Hugh', 'Alexis',
    'Luther', 'Lydia', 'Tommy', 'Leona', 'Guy', 'Wendy', 'Derek', 'Sadie', 'Jesus', 'Monica',
    'Ricky', 'Madison', 'Homer', 'Veronica', 'Everett', 'Joanne', 'Johnnie', 'Susie', 'Randall', 'Sheila',
    'Max', 'Alyssa', 'Glen', 'Valerie', 'Cameron', 'Courtney', 'Evan', 'Cindy', 'Oliver', 'Marian',
    'Logan', 'Roberta', 'Dustin', 'Allison', 'Dean', 'Beulah', 'Sidney', 'Eileen', 'Ronnie', 'April',
    'Luke', 'Suzanne', 'Arnold', 'Wilma', 'Barry', 'Jeanette', 'Elijah', 'Sherry', 'Dan', 'Marguerite',
    'Jimmie', 'Abigail', 'Gene', 'Darlene', 'Jared', 'Michele', 'Caleb', 'Erica', 'Marion', 'Vanessa',
    'Adrian', 'Della', 'Willard', 'Gail', 'Mitchell', 'Alicia', 'Shane', 'Violet', 'Darrell', 'Regina',
    'Wallace', 'Harriet', 'Julius', 'Madeline', 'Corey', 'Sophia', 'Clayton', 'Kristen', 'Jon', 'Melanie',
    'Roland', 'Jill', 'Julian', 'Flora', 'Virgil', 'Jo', 'Ian', 'Jeanne', 'Morris', 'May',
    'Lonnie', 'Nettie', 'Horace', 'Effie', 'Micheal', 'Nina', 'Chris', 'Leah', 'Ira', 'Rhonda',
    'Angel', 'Amelia', 'Clinton', 'Annette', 'Archie', 'Sue', 'Bob', 'Jasmine', 'Miguel', 'Genevieve',
    'Brett', 'Rosemary', 'Hunter', 'Naomi', 'Seth', 'Brianna', 'Wilbur', 'Holly', 'Jeff', 'Arlene',
    'Earnest', 'Hilda', 'Jake', 'Sallie', 'Marshall', 'Alexandra', 'Otto', 'Joann', 'Karl', 'Renee',
    'Ivan', 'Yvonne', 'Mario', 'Lola', 'Erik', 'Constance', 'Otis', 'Kristin', 'Jeremiah', 'Velma',
    'Isaiah', 'Claire', 'Owen', 'Olive', 'Duane', 'Lottie', 'Hubert', 'Tara', 'Brent', 'Eunice',
    'Ed', 'Lizzie', 'Willis', 'Debbie', 'Francisco', 'Inez', 'Marc', 'Kim', 'Perry', 'Colleen',
    'Trevor', 'Beth', 'Derrick', 'Stacy', 'Jackson', 'Margie', 'Nelson', 'Rosie', 'Bert', 'Maxine',
    'Grant', 'Isabella', 'Ross', 'Patsy', 'Lucas', 'Cathy', 'Neil', 'Geneva', 'Ruben', 'Laurie',
    'Dave', 'Delores', 'Mason', 'Alberta', 'Connor', 'Marlene', 'Reginald', 'Cassandra', 'Allan', 'Marcia',
    'Ricardo', 'Brooke', 'Clifton', 'Etta', 'Devin', 'Maureen', 'Blake', 'Verna', 'Dominic', 'Addie',
    'Abraham', 'Carmen', 'Cory', 'Claudia', 'Rudolph', 'Opal', 'Garrett', 'Molly', 'Preston', 'Henrietta',
    'Spencer', 'Gina', 'Charley', 'Stacey', 'August', 'Miriam', 'Grover', 'Vicki', 'Irving', 'Isabel',
    'Felix', 'Joy', 'Bennie', 'Sophie', 'Byron', 'Charlene', 'Ted', 'Estelle', 'Taylor', 'Carla',
    'Edmund', 'Lindsey', 'Rufus', 'Mable', 'Levi', 'Priscilla', 'Andre', 'Carole', 'Jorge', 'Kate',
    'Emil', 'Irma', 'Mack', 'Mollie', 'Casey', 'Chelsea', 'Fredrick', 'Terri', 'Percy', 'Deanna',
    'Andy', 'Melinda', 'Sylvester', 'Heidi', 'Alejandro', 'Janie', 'Roberto', 'Gwendolyn', 'Dwight', 'Kristina',
    'Freddie', 'Eula', 'Pedro', 'Shelby', 'Chase', 'Ora', 'Lance', 'Haley', 'Orville', 'Kaitlyn',
    'Angelo', 'Olga', 'Darren', 'Tamara', 'Harrison', 'Sydney', 'Gavin', 'Kelsey', 'Wade', 'Tonya',
    'Hector', 'Lela', 'Colin', 'Iva', 'Lyle', 'Cecilia', 'Jackie', 'Sabrina', 'Ramon', 'Jenna',
    'Dewey', 'Angelina', 'Elbert', 'Lindsay', 'Emmett', 'Chloe', 'Irvin', 'Kay', 'Mathew', 'Glenda',
    'Kelly', 'Tanya', 'Cole', 'Yolanda', 'Ellis', 'Antoinette', 'Darryl', 'Essie', 'Forrest', 'Erma',
    'Delbert', 'Jeannette', 'Pete', 'Erika', 'Amos', 'Nannie', 'Tim', 'Savannah', 'Wilson', 'Goldie',
    'Simon', 'Bobbie', 'Riley', 'Destiny', 'Stuart', 'Celia', 'Jamie', 'Estella', 'Malcolm', 'Isabelle',
    'Eduardo', 'Ava', 'Alonzo', 'Eliza', 'Fernando', 'Faye', 'Alton', 'Brandy', 'Kurt', 'Paige',
    'Cornelius', 'Faith', 'Salvatore', 'Winifred', 'Leland', 'Marsha', 'Nick', 'Joanna', 'Sherman', 'Vickie',
    'Brad', 'Gabrielle', 'Raul', 'Marissa', 'Omar', 'Rosalie', 'Rex', 'Katelyn', 'Eli', 'Josie',
    'Bryce', 'Cecelia', 'Lynn', 'Muriel', 'Neal', 'Matilda', 'Ervin', 'Brandi', 'Moses', 'Lucile',
    'Xavier', 'Christy', 'Johnathan', 'Maud', 'Tyrone', 'Alison', 'Javier', 'Hailey', 'Rick', 'Dianne',
    'Wilbert', 'Toni', 'Jess', 'Caitlin', 'Wendell', 'Marcella', 'Roosevelt', 'Lily', 'Harley', 'Katrina',
    'Brendan', 'Jenny', 'Laurence', 'Freda', 'Dwayne', 'Felicia', 'Greg', 'Lila', 'Myron', 'Penny',
    'Carroll', 'Bridget', 'Rafael', 'Ola', 'Woodrow', 'Miranda', 'Carlton', 'Myra', 'Loren', 'Mia',
    'Dallas', 'Alta', 'Gerard', 'Ina', 'Aidan', 'Callie', 'Terrence', 'Iris', 'Reuben', 'Kara',
    'Dalton', 'Natasha', 'Kent', 'Jacquelyn', 'Dominick', 'Meghan', 'Adolph', 'Allie', 'Sebastian', 'Luella',
    'Roscoe', 'Misty', 'Dakota', 'Whitney', 'Wyatt', 'Lora', 'Clark', 'Adeline', 'Lowell', 'Bethany',
    'Miles', 'Ana', 'Grady', 'Tracey', 'Lorenzo', 'Bettie', 'Armando', 'Fern', 'Tanner', 'Becky',
    'Randolph', 'Hope', 'Andres', 'Rena', 'Carter', 'Mackenzie', 'Emanuel', 'Rachael', 'Jasper', 'Shelly',
    'Landon', 'Kristine', 'Kirk', 'Candace', 'Brady', 'Ramona', 'Tracy', 'Kendra', 'Shaun', 'Mariah',
    'Wilfred', 'Sherri', 'Jayden', 'Lynda', 'Terrance', 'Autumn', 'Maxwell', 'Jodi', 'Tristan', 'Sierra',
    'Donnie', 'Nell', 'Nicolas', 'Delia', 'Merle', 'Lulu', 'Tommie', 'Karla', 'Diego', 'Gracie',
    'Johnie', 'Elva', 'Daryl', 'Flossie', 'Benny', 'Belle', 'Gus', 'Frieda', 'Drew', 'Angelica',
    'Carson', 'Kristi', 'Hayden', 'Johanna', 'Aiden', 'Briana', 'Sergio', 'Monique', 'Damon', 'Alexandria',
    'Elias', 'Sheryl', 'Jaime', 'Melody', 'Jonathon', 'Desiree', 'Dana', 'Brittney', 'Alberto', 'Adele',
    'Junior', 'Ernestine', 'Ollie', 'Kelli', 'Colton', 'Lou', 'Devon', 'Eloise', 'Conrad', 'Angie',
    'Rickey', 'Augusta', 'Nolan', 'Alexa', 'Kristopher', 'Jocelyn', 'Parker', 'Millie', 'Marco', 'Krista',
    'Dick', 'Katharine', 'Alfredo', 'Kaylee', 'Louie', 'Shelley', 'Aubrey', 'Maryann', 'Cesar', 'Meredith',
    'Julio', 'Marianne', 'Israel', 'Kristy', 'Erick', 'Selma', 'Cleveland', 'Corinne', 'Billie', 'Leila',
    'Collin', 'Zoe', 'Rudy', 'Patty', 'Micah', 'Krystal', 'Rene', 'Lorena', 'Noel', 'Breanna',
    'Enrique', 'Adrienne', 'Solomon', 'Leola', 'Geoffrey', 'Guadalupe', 'Anton', 'Lorene', 'Shannon', 'Fay',
    'Boyd', 'Lenora', 'Loyd', 'Jillian', 'Claud', 'Belinda', 'Edmond', 'Sandy', 'Silas', 'Gayle',
    'Morgan', 'Dorothea', 'Bryant', 'Cleo', 'Roderick', 'Sonia', 'Alfonso', 'Kylie', 'Millard', 'Winnie',
    'Orlando', 'Candice', 'Arturo', 'Adriana', 'Dillon', 'Bernadette', 'Clay', 'Sonya', 'Stewart', 'Rebekah',
    'Monroe', 'Virgie', 'Garry', 'Makayla', 'Damian', 'Nadine', 'Sammy', 'Bailey', 'Elwood', 'Jewel',
]
FIEND_COP_CHANCE = 0.10
FIEND_FINE = 1000
FIEND_NEARBY_COUNT = 1
FIEND_SPAWN_INTERVAL_SECONDS = 300
FIEND_RADIUS_M = 1000
FIEND_EXPIRY_HOURS = 24


def _fiend_pairs():
    out = []
    for i in range(5):
        for j in range(i + 1, 5):
            out.append((FIEND_ITEM_IDS[i], FIEND_ITEM_IDS[j]))
    return out


def _fiend_triples():
    out = []
    for i in range(5):
        for j in range(i + 1, 5):
            for k in range(j + 1, 5):
                out.append((FIEND_ITEM_IDS[i], FIEND_ITEM_IDS[j], FIEND_ITEM_IDS[k]))
    return out


def fiend_variant(variant_id):
    """Deterministic variant catalog: id 0-999 -> unique bundle + payout.

    ids 0-24: singles (5 items x 5 qty). 25-274: pairs (10 pairs x 25 qty
    combos). 275-999: triples (first 725 of 1250 in lex order).
    """
    if not isinstance(variant_id, int) or variant_id < 0 or variant_id >= 1000:
        raise ValueError("variant_id must be 0-999")
    if variant_id < 25:
        ids = [FIEND_ITEM_IDS[variant_id // 5]]
        qtys = [(variant_id % 5) + 1]
    elif variant_id < 275:
        j = variant_id - 25
        ids = list(_fiend_pairs()[j // 25])
        qtys = [(j // 5) % 5 + 1, (j % 5) + 1]
    else:
        j = variant_id - 275
        ids = list(_fiend_triples()[j // 125])
        t = j % 125  # qty combos cycle 0-124 inside each triple
        qtys = [(t // 25) + 1, ((t // 5) % 5) + 1, (t % 5) + 1]
    items = []
    payout = 0
    for item_id, qty in zip(ids, qtys):
        name, _regular, fiend_price = FIEND_ITEM_PRICES[item_id]
        items.append({"item_id": item_id, "name": name, "qty": qty, "unit_price": fiend_price, "line_total": qty * fiend_price})
        payout += qty * fiend_price
    return {"variant_id": variant_id, "items": items, "payout": payout}


def _fiend_inventory_qty(inv, item_id):
    """Oz of item_id in a stacked inventory (dicts or bare strings)."""
    for _it in inv:
        if isinstance(_it, dict) and _it.get("item_id") == item_id:
            return _it.get("qty", 1)
        if isinstance(_it, str) and _it == item_id:
            return 1
    return 0


def _fiend_deduct(inv, item_id, qty):
    """Deduct qty oz of item_id from inv in place; returns oz left."""
    for _i, _it in enumerate(inv):
        if isinstance(_it, dict) and _it.get("item_id") == item_id:
            have = _it.get("qty", 1)
            if have <= qty:
                inv.pop(_i)
                return 0
            inv[_i]["qty"] = have - qty
            return have - qty
        if isinstance(_it, str) and _it == item_id:
            inv.pop(_i)
            return 0
    return 0


@api_router.get("/fiends/nearby")
async def get_fiends_nearby(latitude: float, longitude: float, player_id: str = ""):
    """Fiend missions near a location: buy the five enemy-drop items at +25%."""
    position = Position(latitude=latitude, longitude=longitude)
    await db.fiend_missions.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
    existing = await db.fiend_missions.find({"expires_at": {"$gt": datetime.utcnow()}}).to_list(50)
    nearby = []
    for m in existing:
        if calculate_distance(position, Position(**m["position"])) >= FIEND_RADIUS_M:
            continue
        if player_id and player_id in m.get("attempted_by", []):
            continue
        nearby.append(serialize_doc(m))
    # ONE Fiend at a time: if one is already active, return it as-is.
    if nearby:
        return nearby[:1]
    # No active Fiend: a new one spawns only after the periodic interval
    # since this player's last completed Fiend (mirrors the monsters'
    # "1 more every 5 minutes" cadence). First Fiend ever has no cooldown.
    if player_id:
        _p = await db.players.find_one({"id": player_id})
        _last = (_p or {}).get("last_fiend_completed_at")
        if _last:
            try:
                _last_dt = datetime.fromisoformat(_last) if isinstance(_last, str) else _last
                if (datetime.utcnow() - _last_dt).total_seconds() < FIEND_SPAWN_INTERVAL_SECONDS:
                    return []
            except ValueError:
                pass
    variant_id = random.randint(0, 999)
    variant = fiend_variant(variant_id)
    offset_lat = random.uniform(-0.005, 0.005)
    offset_lon = random.uniform(-0.005, 0.005)
    fiend = {
        "id": "fiend_" + str(uuid.uuid4())[:8],
        "name": FIEND_NAMES[variant_id],
        "variant_id": variant_id,
        "items": variant["items"],
        "payout": variant["payout"],
        "position": {"latitude": latitude + offset_lat, "longitude": longitude + offset_lon},
        "expires_at": datetime.utcnow() + timedelta(hours=FIEND_EXPIRY_HOURS),
        "attempted_by": [],
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.fiend_missions.insert_one(fiend)
    nearby.append(serialize_doc(fiend))
    return nearby


@api_router.post("/fiends/{fiend_id}/complete")
async def complete_fiend(fiend_id: str, player_id: str):
    """Sell the requested items to a Fiend at +25%. Flat 10% chance the
    Fiend is an undercover cop: items are confiscated and the player is
    fined $1000 (capped at current cash). One attempt per Fiend per player."""
    fiend = await db.fiend_missions.find_one({"id": fiend_id})
    if not fiend:
        raise HTTPException(status_code=404, detail="Fiend not found")
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if player_id in fiend.get("attempted_by", []):
        raise HTTPException(status_code=400, detail="You already tried this Fiend")
    # The player must hold every requested item to attempt the sale.
    # A failed check does NOT consume the attempt.
    inv = player.get("inventory", [])
    for _req in fiend.get("items", []):
        if _fiend_inventory_qty(inv, _req["item_id"]) < _req["qty"]:
            raise HTTPException(status_code=400, detail=f"Not enough {_req['name']} - need {_req['qty']} oz")
    # FIEND_COP_ROLL: flat 10% at completion time, hidden until the attempt.
    is_cop = random.random() < FIEND_COP_CHANCE
    # Consume the attempt atomically: only the first attempt for this player
    # can win the update; a retry (or double-tap) sees modified_count 0.
    marked = await db.fiend_missions.update_one(
        {"id": fiend_id, "attempted_by": {"$ne": player_id}},
        {"$addToSet": {"attempted_by": player_id}},
    )
    if marked.modified_count == 0:
        raise HTTPException(status_code=400, detail="You already tried this Fiend")
    # The items leave the inventory on EITHER outcome (sold, or confiscated).
    for _req in fiend.get("items", []):
        _fiend_deduct(inv, _req["item_id"], _req["qty"])
    _now_iso = datetime.utcnow().isoformat()
    if is_cop:
        fine = min(FIEND_FINE, player.get("cash", 0))
        await db.players.update_one({"id": player_id}, {"$set": {"inventory": inv, "last_fiend_completed_at": _now_iso}, "$inc": {"cash": -fine}})
        return {
            "outcome": "cop",
            "fiend_name": fiend.get("name", "Fiend"),
            "message": f"Undercover cop! Your goods were confiscated and you were fined ${fine}.",
            "fined": fine,
            "items": fiend.get("items", []),
            "cash": player.get("cash", 0) - fine,
        }
    payout = fiend.get("payout", 0)
    await db.players.update_one({"id": player_id}, {"$set": {"inventory": inv, "last_fiend_completed_at": _now_iso}, "$inc": {"cash": payout}})
    return {
        "outcome": "sold",
        "fiend_name": fiend.get("name", "Fiend"),
        "message": f"Sold to the Fiend for ${payout}!",
        "payout": payout,
        "cash_gained": payout,
        "items": fiend.get("items", []),
        "cash": player.get("cash", 0) + payout,
    }

'''

# (item_id, display name, route id) for the five dedicated sell endpoints.
SELL_ITEMS = [
    ("grass", "Grass"),
    ("pills", "Pills"),
    ("rock_candy", "Rock Candy"),
    ("flake", "Flake"),
    ("brown_sugar", "Brown Sugar"),
]


def delta(s):
    return (s.count("{"), s.count("}"), s.count("("), s.count(")"), s.count("["), s.count("]"))


def main():
    landed = []
    warned = []
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - Fiend missions NOT added")
        return
    src = SERVER.read_text(errors="ignore")
    orig = src
    d0 = delta(src)

    # --- Part 0: imports the fiend code needs (random/datetime/timedelta/uuid) ---
    for name in ("import random", "from datetime import datetime, timedelta", "import uuid"):
        if name not in src:
            print(f"WARNING: '{name}' not found in server.py - fiend code may fail at runtime")
            warned.append("imports")

    # --- Part 1: variant catalog + spawn/complete routes ---
    if "def fiend_variant" in src and "get_fiends_nearby" in src and "complete_fiend" in src:
        print("FIEND_BACKEND_ROUTES_ALREADY_APPLIED")
        landed.append("routes")
    else:
        anchor = '@api_router.get("/missions/active/{player_id}")'
        if anchor in src:
            src = src.replace(anchor, FIEND_CODE + anchor, 1)
            print("FIEND_BACKEND_ROUTES_OK")
            landed.append("routes")
        else:
            print("WARNING: missions/active anchor not found - Fiend routes NOT added")
            warned.append("routes")

    # --- Part 2: SELL enforcement on the five dedicated sell endpoints ---
    for item_id, name in SELL_ITEMS:
        guard = f'    raise HTTPException(status_code=400, detail="{name} can only be sold to a Fiend now. Find a 🧟 on the map.")'
        deco = f'@api_router.post("/players/{{player_id}}/{item_id}/sell")'
        if guard in src:
            print(f"FIEND_BACKEND_SELL_{item_id.upper()}_ALREADY_APPLIED")
            landed.append(f"sell-{item_id}")
            continue
        di = src.find(deco)
        if di == -1:
            print(f"WARNING: {name} sell endpoint not found - SELL enforcement NOT added for {name}")
            warned.append(f"sell-{item_id}")
            continue
        # Insert the guard as the first statement after the def line.
        nl = src.find("\n", di)
        def_end = src.find("\n", nl + 1)
        if def_end == -1 or "async def " not in src[nl:def_end + 1]:
            print(f"WARNING: {name} sell endpoint def line not found - SELL enforcement NOT added for {name}")
            warned.append(f"sell-{item_id}")
            continue
        src = src[:def_end + 1] + guard + "\n" + src[def_end + 1:]
        print(f"FIEND_BACKEND_SELL_{item_id.upper()}_OK")
        landed.append(f"sell-{item_id}")

    # --- Part 3: generic sell endpoint must also reject the five items ---
    generic_guard = (
        '    if item_id in ("grass", "pills", "rock_candy", "flake", "brown_sugar"):\n'
        '        raise HTTPException(status_code=400, detail="That item can only be sold to a Fiend now. Find a 🧟 on the map.")\n'
    )
    if generic_guard in src:
        print("FIEND_BACKEND_SELL_GENERIC_ALREADY_APPLIED")
        landed.append("sell-generic")
    else:
        def_line = "async def sell_item(player_id: str, item_id: str):"
        if def_line in src:
            src = src.replace(def_line, def_line + "\n" + generic_guard.rstrip("\n"), 1)
            print("FIEND_BACKEND_SELL_GENERIC_OK")
            landed.append("sell-generic")
        else:
            print("WARNING: generic sell endpoint not found - generic SELL enforcement NOT added")
            warned.append("sell-generic")

    d = delta(src)
    if (d[0] - d[1]) != (d0[0] - d0[1]) or (d[2] - d[3]) != (d0[2] - d0[3]) or (d[4] - d[5]) != (d0[4] - d0[5]):
        print("WARNING: unbalanced brackets - server.py NOT written")
        return
    if src != orig:
        SERVER.write_text(src)
    if warned:
        print("FIEND_BACKEND_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warned) + ")")
    else:
        print("FIEND_BACKEND_OK")


if __name__ == "__main__":
    main()
