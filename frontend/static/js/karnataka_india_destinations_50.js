/**
 * 50 Curated Famous Indian Tourist Destinations for Ripple Transition
 * 25 Top Highlights from Karnataka + 25 Iconic All-India Highlights
 * High-resolution 1800w photography, taglines, and direct planner routing.
 */

(function (global) {
  "use strict";

  const uPhoto = (id) =>
    `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&q=85&w=1800`;

  global.KARNATAKA_INDIA_DESTINATIONS_50 = [
    // ── 25 Karnataka Destinations ──────────────────────────────────
    {
      title: "Coorg (Kodagu)",
      searchKey: "Coorg",
      state: "Karnataka",
      tagline: "Scotland of India · Misty Hills & Coffee Estates",
      image: uPhoto("1596422846543-75c6fc197f07"),
      planUrl: "/planner/new?destination=Coorg&source=Bengaluru"
    },
    {
      title: "Chikmagalur",
      searchKey: "Chikmagalur",
      state: "Karnataka",
      tagline: "Mullayanagiri Peak & Sprawling Arabica Plantations",
      image: uPhoto("1588714477688-cf28a50e94f7"),
      planUrl: "/planner/new?destination=Chikmagalur&source=Bengaluru"
    },
    {
      title: "Hampi",
      searchKey: "Hampi",
      state: "Karnataka",
      tagline: "UNESCO World Heritage & Ancient Vijayanagara Ruins",
      image: uPhoto("1590050752117-238cb0fb12b1"),
      planUrl: "/planner/new?destination=Hampi&source=Bengaluru"
    },
    {
      title: "Mysore Palace",
      searchKey: "Mysore",
      state: "Karnataka",
      tagline: "The City of Palaces & Royal Dasara Heritage",
      image: uPhoto("1582510003544-4d00b7f74220"),
      planUrl: "/planner/new?destination=Mysore&source=Bengaluru"
    },
    {
      title: "Gokarna (Om Beach)",
      searchKey: "Gokarna",
      state: "Karnataka",
      tagline: "Pristine Arabian Cliffs, Sacred Shores & Kudle Beach",
      image: uPhoto("1507525428034-b723cf961d3e"),
      planUrl: "/planner/new?destination=Gokarna&source=Bengaluru"
    },
    {
      title: "Jog Falls (Shivamogga)",
      searchKey: "Jog Falls",
      state: "Karnataka",
      tagline: "India's Majestic 830ft Plunge Waterfall Cascade",
      image: uPhoto("1546182990-dffeafbe841d"),
      planUrl: "/planner/new?destination=Jog%20Falls&source=Bengaluru"
    },
    {
      title: "Badami Cave Temples",
      searchKey: "Badami",
      state: "Karnataka",
      tagline: "6th-Century Chalukya Rock-Cut Red Sandstone Marvels",
      image: uPhoto("1598890777032-bde835ba27c2"),
      planUrl: "/planner/new?destination=Badami&source=Bengaluru"
    },
    {
      title: "Murudeshwar",
      searchKey: "Murudeshwar",
      state: "Karnataka",
      tagline: "World's Second Tallest Shiva Statue & Coastal Temple",
      image: uPhoto("1561361513-2d000a50f0dc"),
      planUrl: "/planner/new?destination=Murudeshwar&source=Bengaluru"
    },
    {
      title: "Bandipur National Park",
      searchKey: "Bandipur",
      state: "Karnataka",
      tagline: "Nilgiri Biosphere & Royal Bengal Tiger Safari",
      image: uPhoto("1561731216-c3a4d99437d5"),
      planUrl: "/planner/new?destination=Bandipur&source=Bengaluru"
    },
    {
      title: "Dandeli",
      searchKey: "Dandeli",
      state: "Karnataka",
      tagline: "Kali River White Water Rafting & Dense Canopy Walks",
      image: uPhoto("1501785888041-af3ef285b470"),
      planUrl: "/planner/new?destination=Dandeli&source=Hubli"
    },
    {
      title: "Kabini",
      searchKey: "Kabini",
      state: "Karnataka",
      tagline: "Nagarhole River Safari & Black Panther Reserve",
      image: uPhoto("1546182990-dffeafbe841d"),
      planUrl: "/planner/new?destination=Kabini&source=Mysore"
    },
    {
      title: "Belur & Halebidu",
      searchKey: "Belur",
      state: "Karnataka",
      tagline: "12th-Century Hoysala Soapstone Architectural Wonders",
      image: uPhoto("1582510003544-4d00b7f74220"),
      planUrl: "/planner/new?destination=Belur&source=Bengaluru"
    },
    {
      title: "Kudremukh",
      searchKey: "Kudremukh",
      state: "Karnataka",
      tagline: "Horse-Faced Grassland Peaks & Shola Rainforests",
      image: uPhoto("1464822759023-fed622ff2c3b"),
      planUrl: "/planner/new?destination=Kudremukh&source=Mangalore"
    },
    {
      title: "Agumbe",
      searchKey: "Agumbe",
      state: "Karnataka",
      tagline: "Cherrapunji of the South & Breathtaking Ghat Sunsets",
      image: uPhoto("1501785888041-af3ef285b470"),
      planUrl: "/planner/new?destination=Agumbe&source=Shivamogga"
    },
    {
      title: "Udupi (Malpe Beach)",
      searchKey: "Udupi",
      state: "Karnataka",
      tagline: "Columnar Basalt St. Mary's Island & Sacred Temples",
      image: uPhoto("1507525428034-b723cf961d3e"),
      planUrl: "/planner/new?destination=Udupi&source=Mangalore"
    },
    {
      title: "Nagarhole National Park",
      searchKey: "Nagarhole",
      state: "Karnataka",
      tagline: "Kabini Backwaters & Asian Wild Elephant Herds",
      image: uPhoto("1575550959106-5a7defe28b56"),
      planUrl: "/planner/new?destination=Nagarhole&source=Mysore"
    },
    {
      title: "Shravanabelagola",
      searchKey: "Shravanabelagola",
      state: "Karnataka",
      tagline: "World-Renowned 57ft Monolithic Gommateshwara Statue",
      image: uPhoto("1590050752117-238cb0fb12b1"),
      planUrl: "/planner/new?destination=Shravanabelagola&source=Bengaluru"
    },
    {
      title: "Pattadakal",
      searchKey: "Pattadakal",
      state: "Karnataka",
      tagline: "UNESCO 7th-Century Temple Complex on Malaprabha River",
      image: uPhoto("1598890777032-bde835ba27c2"),
      planUrl: "/planner/new?destination=Pattadakal&source=Belgaum"
    },
    {
      title: "Shivanasamudra Falls",
      searchKey: "Shivanasamudra",
      state: "Karnataka",
      tagline: "Twin Gaganachukki & Bharachukki Kaveri Cascades",
      image: uPhoto("1506744038136-46273834b3fb"),
      planUrl: "/planner/new?destination=Shivanasamudra&source=Bengaluru"
    },
    {
      title: "Madikeri Fort & Raja's Seat",
      searchKey: "Madikeri",
      state: "Karnataka",
      tagline: "Panoramic Sunset Vistas of Kodagu Hill Country",
      image: uPhoto("1596422846543-75c6fc197f07"),
      planUrl: "/planner/new?destination=Madikeri&source=Bengaluru"
    },
    {
      title: "Kemmangundi",
      searchKey: "Kemmangundi",
      state: "Karnataka",
      tagline: "KR Hills, Hebbe Falls & Rose Gardens in Baba Budan",
      image: uPhoto("1588714477688-cf28a50e94f7"),
      planUrl: "/planner/new?destination=Kemmangundi&source=Chikmagalur"
    },
    {
      title: "Nandi Hills",
      searchKey: "Nandi Hills",
      state: "Karnataka",
      tagline: "Ancient Sunrise Cloud Fortress & Tipu's Drop",
      image: uPhoto("1506461883276-594a12b11cf3"),
      planUrl: "/planner/new?destination=Nandi%20Hills&source=Bengaluru"
    },
    {
      title: "Chitradurga Fort",
      searchKey: "Chitradurga",
      state: "Karnataka",
      tagline: "Historical Fort of Seven Concentric Rounds & Stone Gates",
      image: uPhoto("1590050752117-238cb0fb12b1"),
      planUrl: "/planner/new?destination=Chitradurga&source=Bengaluru"
    },
    {
      title: "BR Hills (Biligirirangana)",
      searchKey: "BR Hills",
      state: "Karnataka",
      tagline: "Ecological Bridge Between Eastern & Western Ghats",
      image: uPhoto("1448375240586-882707db888b"),
      planUrl: "/planner/new?destination=BR%20Hills&source=Mysore"
    },
    {
      title: "Sakleshpur",
      searchKey: "Sakleshpur",
      state: "Karnataka",
      tagline: "Star-Shaped Manjarabad Fort & Green Railway Treks",
      image: uPhoto("1588714477688-cf28a50e94f7"),
      planUrl: "/planner/new?destination=Sakleshpur&source=Bengaluru"
    },

    // ── 25 Iconic All-India Destinations ────────────────────────────
    {
      title: "Varanasi",
      searchKey: "Varanasi",
      state: "Uttar Pradesh",
      tagline: "Ancient Spiritual Ghats & Sacred Ganga Aarti",
      image: uPhoto("1561361513-2d000a50f0dc"),
      planUrl: "/planner/new?destination=Varanasi&source=Delhi"
    },
    {
      title: "Taj Mahal, Agra",
      searchKey: "Agra",
      state: "Uttar Pradesh",
      tagline: "Eternal Monument of Love & Mughal Architecture Wonder",
      image: uPhoto("1564507592333-c60657eea523"),
      planUrl: "/planner/new?destination=Agra&source=Delhi"
    },
    {
      title: "Udaipur",
      searchKey: "Udaipur",
      state: "Rajasthan",
      tagline: "City of Lakes & Shimmering Lake Pichola Palaces",
      image: uPhoto("1615836245337-f5b9b2303f10"),
      planUrl: "/planner/new?destination=Udaipur&source=Ahmedabad"
    },
    {
      title: "Jaipur (The Pink City)",
      searchKey: "Jaipur",
      state: "Rajasthan",
      tagline: "Hawa Mahal, Amer Fort & Royal Heritage Grandeur",
      image: uPhoto("1599661046289-e31897846e41"),
      planUrl: "/planner/new?destination=Jaipur&source=Delhi"
    },
    {
      title: "Leh Ladakh",
      searchKey: "Leh",
      state: "Ladakh",
      tagline: "Pangong Tso, Khardung La & High Himalayan Monasteries",
      image: uPhoto("1581793745862-99fde7fa73d2"),
      planUrl: "/planner/new?destination=Leh&source=Delhi"
    },
    {
      title: "Manali",
      searchKey: "Manali",
      state: "Himachal Pradesh",
      tagline: "Snow-Capped Solang Valley & Rohtang Pass Adventures",
      image: uPhoto("1626621341517-bbf3d9990a23"),
      planUrl: "/planner/new?destination=Manali&source=Delhi"
    },
    {
      title: "Munnar",
      searchKey: "Munnar",
      state: "Kerala",
      tagline: "Endless Rolling Tea Valleys & Anamudi Mountain Mist",
      image: uPhoto("1593693397690-362cb9666fc2"),
      planUrl: "/planner/new?destination=Munnar&source=Kochi"
    },
    {
      title: "Alleppey (Alappuzha)",
      searchKey: "Alleppey",
      state: "Kerala",
      tagline: "Venice of the East & Serene Backwater Houseboat Loops",
      image: uPhoto("1602216056096-3b40cc0c9944"),
      planUrl: "/planner/new?destination=Alleppey&source=Kochi"
    },
    {
      title: "South Goa",
      searchKey: "Goa",
      state: "Goa",
      tagline: "Palolem Sunsets, Portuguese Forts & Golden Sands",
      image: uPhoto("1512343879784-a960bf40e7f2"),
      planUrl: "/planner/new?destination=Goa&source=Mumbai"
    },
    {
      title: "Rishikesh",
      searchKey: "Rishikesh",
      state: "Uttarakhand",
      tagline: "Yoga Capital of the World & Holy Ganga River Rafting",
      image: uPhoto("1598890777032-bde835ba27c2"),
      planUrl: "/planner/new?destination=Rishikesh&source=Delhi"
    },
    {
      title: "Ooty",
      searchKey: "Ooty",
      state: "Tamil Nadu",
      tagline: "Queen of Hill Stations & Nilgiri Mountain Railway",
      image: uPhoto("1589182373726-e4f658ab50f0"),
      planUrl: "/planner/new?destination=Ooty&source=Coimbatore"
    },
    {
      title: "Darjeeling",
      searchKey: "Darjeeling",
      state: "West Bengal",
      tagline: "Kanchenjunga Sunrise from Tiger Hill & Himalayan Tea",
      image: uPhoto("1544735716-392fe2489ffa"),
      planUrl: "/planner/new?destination=Darjeeling&source=Kolkata"
    },
    {
      title: "Golden Temple, Amritsar",
      searchKey: "Amritsar",
      state: "Punjab",
      tagline: "Spiritual Sanctum of Sikhism & Wagah Border Ceremony",
      image: uPhoto("1584551246679-0daf3d275d0f"),
      planUrl: "/planner/new?destination=Amritsar&source=Delhi"
    },
    {
      title: "Jaisalmer",
      searchKey: "Jaisalmer",
      state: "Rajasthan",
      tagline: "Sam Sand Dunes, Camel Treks & Living Golden Fort",
      image: uPhoto("1509316975850-ff9c5deb0cd9"),
      planUrl: "/planner/new?destination=Jaisalmer&source=Jodhpur"
    },
    {
      title: "Spiti Valley",
      searchKey: "Spiti",
      state: "Himachal Pradesh",
      tagline: "Cold Desert Monasteries & High Altitude Stargazing",
      image: uPhoto("1527630941-4a229fd674ab"),
      planUrl: "/planner/new?destination=Spiti&source=Shimla"
    },
    {
      title: "Pondicherry",
      searchKey: "Pondicherry",
      state: "Tamil Nadu",
      tagline: "French Colonial Quarter & Serene Promenade Walks",
      image: uPhoto("1582510003544-4d00b7f74220"),
      planUrl: "/planner/new?destination=Pondicherry&source=Chennai"
    },
    {
      title: "Kodaikanal",
      searchKey: "Kodaikanal",
      state: "Tamil Nadu",
      tagline: "Star-Shaped Lake, Pillar Rocks & Pine Valley Treks",
      image: uPhoto("1588714477688-cf28a50e94f7"),
      planUrl: "/planner/new?destination=Kodaikanal&source=Madurai"
    },
    {
      title: "Srinagar & Dal Lake",
      searchKey: "Srinagar",
      state: "Jammu & Kashmir",
      tagline: "Shikara Rides, Floating Lotus Gardens & Snow Peaks",
      image: uPhoto("1486870591958-9b9d0d1dda99"),
      planUrl: "/planner/new?destination=Srinagar&source=Delhi"
    },
    {
      title: "Jodhpur (The Blue City)",
      searchKey: "Jodhpur",
      state: "Rajasthan",
      tagline: "Mehrangarh Fort Overlooking the Azure Old City",
      image: uPhoto("1524492412937-b28074a5d7da"),
      planUrl: "/planner/new?destination=Jodhpur&source=Jaipur"
    },
    {
      title: "Shillong & Cherrapunji",
      searchKey: "Shillong",
      state: "Meghalaya",
      tagline: "Living Root Bridges & Spectacular Nohkalikai Cascades",
      image: uPhoto("1506461883276-594a12b11cf3"),
      planUrl: "/planner/new?destination=Shillong&source=Guwahati"
    },
    {
      title: "Andaman Islands",
      searchKey: "Andaman",
      state: "Andaman & Nicobar",
      tagline: "Radhanagar Beach & Vibrant Coral Reef Marine Life",
      image: uPhoto("1507525428034-b723cf961d3e"),
      planUrl: "/planner/new?destination=Andaman&source=Chennai"
    },
    {
      title: "Gangtok",
      searchKey: "Gangtok",
      state: "Sikkim",
      tagline: "Tsomgo Lake, Rumtek & Panoramic Himalayan Horizons",
      image: uPhoto("1589182373726-e4f658ab50f0"),
      planUrl: "/planner/new?destination=Gangtok&source=Siliguri"
    },
    {
      title: "Kaziranga",
      searchKey: "Kaziranga",
      state: "Assam",
      tagline: "UNESCO Sanctuary of the Great Indian One-Horned Rhino",
      image: uPhoto("1575550959106-5a7defe28b56"),
      planUrl: "/planner/new?destination=Kaziranga&source=Guwahati"
    },
    {
      title: "Rann of Kutch",
      searchKey: "Kutch",
      state: "Gujarat",
      tagline: "Endless White Salt Desert & Celebrated Rann Utsav",
      image: uPhoto("1509316975850-ff9c5deb0cd9"),
      planUrl: "/planner/new?destination=Kutch&source=Bhuj"
    },
    {
      title: "Gulmarg & Pahalgam",
      searchKey: "Gulmarg",
      state: "Jammu & Kashmir",
      tagline: "Meadow of Flowers, Apharwat Snow Peak & Lidder River",
      image: uPhoto("1486870591958-9b9d0d1dda99"),
      planUrl: "/planner/new?destination=Gulmarg&source=Srinagar"
    },
    {
      title: "Khajuraho",
      searchKey: "Khajuraho",
      state: "Madhya Pradesh",
      tagline: "UNESCO Medieval Sandstone Temples & Nagara Carvings",
      image: uPhoto("1598890777032-bde835ba27c2"),
      planUrl: "/planner/new?destination=Khajuraho&source=Delhi"
    },
    {
      title: "Varkala",
      searchKey: "Varkala",
      state: "Kerala",
      tagline: "Dramatic Red Sea Cliffs & Holy Papanasam Sunset Beach",
      image: uPhoto("1507525428034-b723cf961d3e"),
      planUrl: "/planner/new?destination=Varkala&source=Trivandrum"
    }
  ];
})(window);
