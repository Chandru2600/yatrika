/**
 * Curated 52 Authentic Indian Destinations for Liquid Glass Carousel
 * Covers top cultural, hill station, coastal, wildlife, and heritage hubs across India.
 */

(function (global) {
  "use strict";

  const photo = (id) =>
    `https://images.unsplash.com/photo-${id}?w=900&h=1200&q=85&auto=format&fit=crop`;

  global.INDIAN_DESTINATIONS_50 = [
    {
      title: "Coorg",
      subtitle: "Karnataka · Coffee & Waterfalls",
      price: "From ₹8,500 / person",
      rating: "⭐ 4.8",
      src: photo("1596422846543-75c6fc197f07"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Coorg&source=Bengaluru"
    },
    {
      title: "Srinagar & Dal Lake",
      subtitle: "Jammu & Kashmir · Shikara Rides & Mughal Gardens",
      price: "From ₹14,800 / person",
      rating: "⭐ 4.9",
      src: photo("1486870591958-9b9d0d1dda99"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Srinagar&source=Delhi"
    },
    {
      title: "Agra (Taj Mahal)",
      subtitle: "Uttar Pradesh · Wonder of the World & Mughal Architecture",
      price: "From ₹5,400 / person",
      rating: "⭐ 4.9",
      src: photo("1564507592333-c60657eea523"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Agra&source=Delhi"
    },
    {
      title: "Chikmagalur",
      subtitle: "Karnataka · Mountain Peaks & Estates",
      price: "From ₹7,200 / person",
      rating: "⭐ 4.7",
      src: photo("1588714477688-cf28a50e94f7"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Chikmagalur&source=Bengaluru"
    },
    {
      title: "Hampi",
      subtitle: "Karnataka · UNESCO World Heritage",
      price: "From ₹6,500 / person",
      rating: "⭐ 4.9",
      src: photo("1590050752117-238cb0fb12b1"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Hampi&source=Bengaluru"
    },
    {
      title: "South Goa",
      subtitle: "Goa · Coastal Sunsets & Forts",
      price: "From ₹9,800 / person",
      rating: "⭐ 4.8",
      src: photo("1512343879784-a960bf40e7f2"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Goa&source=Mumbai"
    },
    {
      title: "Manali",
      subtitle: "Himachal · Snow Valleys & Solang",
      price: "From ₹11,200 / person",
      rating: "⭐ 4.8",
      src: photo("1626621341517-bbf3d9990a23"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Manali&source=Delhi"
    },
    {
      title: "Munnar",
      subtitle: "Kerala · Rolling Tea Gardens & Mist",
      price: "From ₹8,900 / person",
      rating: "⭐ 4.9",
      src: photo("1593693397690-362cb9666fc2"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Munnar&source=Kochi"
    },
    {
      title: "Udaipur",
      subtitle: "Rajasthan · Royal Palaces & Lakes",
      price: "From ₹12,500 / person",
      rating: "⭐ 4.9",
      src: photo("1615836245337-f5b9b2303f10"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Udaipur&source=Ahmedabad"
    },
    {
      title: "Varanasi",
      subtitle: "Uttar Pradesh · Spiritual Ghats & Ganga",
      price: "From ₹6,800 / person",
      rating: "⭐ 4.8",
      src: photo("1561361513-2d000a50f0dc"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Varanasi&source=Delhi"
    },
    {
      title: "Leh Ladakh",
      subtitle: "Ladakh · High Passes & Monasteries",
      price: "From ₹18,500 / person",
      rating: "⭐ 4.9",
      src: photo("1581793745862-99fde7fa73d2"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Leh&source=Delhi"
    },
    {
      title: "Ooty",
      subtitle: "Tamil Nadu · Nilgiri Blue Mountains",
      price: "From ₹7,800 / person",
      rating: "⭐ 4.7",
      src: photo("1589182373726-e4f658ab50f0"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Ooty&source=Bengaluru"
    },
    {
      title: "Rishikesh",
      subtitle: "Uttarakhand · Ganga Aarti & Rafting",
      price: "From ₹6,200 / person",
      rating: "⭐ 4.8",
      src: photo("1598890777032-bde835ba27c2"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Rishikesh&source=Delhi"
    },
    {
      title: "Jaipur",
      subtitle: "Rajasthan · The Pink City & Forts",
      price: "From ₹8,400 / person",
      rating: "⭐ 4.8",
      src: photo("1599661046289-e31897846e41"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Jaipur&source=Delhi"
    },
    {
      title: "Alleppey",
      subtitle: "Kerala · Backwater Houseboats & Canals",
      price: "From ₹9,500 / person",
      rating: "⭐ 4.9",
      src: photo("1602216056096-3b40cc0c9944"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Alleppey&source=Kochi"
    },
    {
      title: "Gokarna",
      subtitle: "Karnataka · Pristine Beaches & Om Beach",
      price: "From ₹6,900 / person",
      rating: "⭐ 4.7",
      src: photo("1507525428034-b723cf961d3e"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Gokarna&source=Bengaluru"
    },
    {
      title: "Darjeeling",
      subtitle: "West Bengal · Kanchenjunga & Toy Train",
      price: "From ₹9,200 / person",
      rating: "⭐ 4.8",
      src: photo("1544735716-392fe2489ffa"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Darjeeling&source=Kolkata"
    },
    {
      title: "Shimla",
      subtitle: "Himachal · Colonial Ridge & Pine Forests",
      price: "From ₹8,600 / person",
      rating: "⭐ 4.7",
      src: photo("1586500036706-41963de24d8b"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Shimla&source=Chandigarh"
    },
    {
      title: "Pondicherry",
      subtitle: "Tamil Nadu · French Quarter & Promenade",
      price: "From ₹7,400 / person",
      rating: "⭐ 4.7",
      src: photo("1582510003544-4d00b7f74220"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Pondicherry&source=Chennai"
    },
    {
      title: "Kodaikanal",
      subtitle: "Tamil Nadu · Princess of Hill Stations",
      price: "From ₹7,600 / person",
      rating: "⭐ 4.8",
      src: photo("1506744038136-46273834b3fb"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Kodaikanal&source=Madurai"
    },
    {
      title: "Jaisalmer",
      subtitle: "Rajasthan · Golden Sand Dunes & Fort",
      price: "From ₹10,500 / person",
      rating: "⭐ 4.8",
      src: photo("1509316975850-ff9c5deb0cd9"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Jaisalmer&source=Jodhpur"
    },
    {
      title: "Wayanad",
      subtitle: "Kerala · Mist, Waterfalls & Edakkal Caves",
      price: "From ₹8,100 / person",
      rating: "⭐ 4.8",
      src: photo("1588714477688-cf28a50e94f7"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Wayanad&source=Calicut"
    },
    {
      title: "Shillong",
      subtitle: "Meghalaya · Scotland of the East",
      price: "From ₹11,000 / person",
      rating: "⭐ 4.9",
      src: photo("1506461883276-594a12b11cf3"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Shillong&source=Guwahati"
    },
    {
      title: "Kasol",
      subtitle: "Himachal · Parvati Valley & Pine Treks",
      price: "From ₹7,500 / person",
      rating: "⭐ 4.7",
      src: photo("1464822759023-fed622ff2c3b"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Kasol&source=Delhi"
    },
    {
      title: "Mount Abu",
      subtitle: "Rajasthan · Oasis in Aravalli Hills",
      price: "From ₹7,900 / person",
      rating: "⭐ 4.6",
      src: photo("1519681393784-d120267933ba"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Mount%20Abu&source=Ahmedabad"
    },
    {
      title: "Mysore",
      subtitle: "Karnataka · Royal Palace & Silk Heritage",
      price: "From ₹5,800 / person",
      rating: "⭐ 4.8",
      src: photo("1582510003544-4d00b7f74220"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Mysore&source=Bengaluru"
    },
    {
      title: "Khajuraho",
      subtitle: "Madhya Pradesh · Ancient Temple Art",
      price: "From ₹6,400 / person",
      rating: "⭐ 4.7",
      src: photo("1598890777032-bde835ba27c2"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Khajuraho&source=Delhi"
    },
    {
      title: "Amritsar",
      subtitle: "Punjab · Golden Temple & Wagah Border",
      price: "From ₹5,900 / person",
      rating: "⭐ 4.9",
      src: photo("1584551246679-0daf3d275d0f"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Amritsar&source=Delhi"
    },
    {
      title: "Spiti Valley",
      subtitle: "Himachal · Cold Desert & Monasteries",
      price: "From ₹16,800 / person",
      rating: "⭐ 4.9",
      src: photo("1527630941-4a229fd674ab"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Spiti&source=Shimla"
    },
    {
      title: "Ranthambore",
      subtitle: "Rajasthan · Tiger Safari & Royal Ruins",
      price: "From ₹13,200 / person",
      rating: "⭐ 4.8",
      src: photo("1561731216-c3a4d99437d5"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Ranthambore&source=Jaipur"
    },
    {
      title: "Andaman Islands",
      subtitle: "Andaman & Nicobar · Coral Reefs & Radhanagar",
      price: "From ₹22,000 / person",
      rating: "⭐ 4.9",
      src: photo("1507525428034-b723cf961d3e"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Andaman&source=Chennai"
    },
    {
      title: "Gangtok",
      subtitle: "Sikkim · Kanchenjunga & Monasteries",
      price: "From ₹10,800 / person",
      rating: "⭐ 4.8",
      src: photo("1589182373726-e4f658ab50f0"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Gangtok&source=Siliguri"
    },
    {
      title: "Kaziranga",
      subtitle: "Assam · One-Horned Rhino Safari",
      price: "From ₹12,400 / person",
      rating: "⭐ 4.8",
      src: photo("1575550959106-5a7defe28b56"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Kaziranga&source=Guwahati"
    },
    {
      title: "Agra",
      subtitle: "Uttar Pradesh · Taj Mahal & Mughal Forts",
      price: "From ₹5,400 / person",
      rating: "⭐ 4.8",
      src: photo("1564507592333-c60657eea523"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Agra&source=Delhi"
    },
    {
      title: "Pushkar",
      subtitle: "Rajasthan · Sacred Lake & Desert Vibes",
      price: "From ₹6,100 / person",
      rating: "⭐ 4.7",
      src: photo("1518684079-3c830dcef090"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Pushkar&source=Jaipur"
    },
    {
      title: "Mahabalipuram",
      subtitle: "Tamil Nadu · Shore Temple & Rock Reliefs",
      price: "From ₹6,700 / person",
      rating: "⭐ 4.7",
      src: photo("1582510003544-4d00b7f74220"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Mahabalipuram&source=Chennai"
    },
    {
      title: "Tawang",
      subtitle: "Arunachal Pradesh · Monasteries & Snow Passes",
      price: "From ₹17,500 / person",
      rating: "⭐ 4.9",
      src: photo("1464822759023-fed622ff2c3b"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Tawang&source=Tezpur"
    },
    {
      title: "Pachmarhi",
      subtitle: "Madhya Pradesh · Queen of Satpura Hills",
      price: "From ₹7,100 / person",
      rating: "⭐ 4.7",
      src: photo("1448375240586-882707db888b"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Pachmarhi&source=Bhopal"
    },
    {
      title: "Cherrapunji",
      subtitle: "Meghalaya · Living Root Bridges & Cascades",
      price: "From ₹11,500 / person",
      rating: "⭐ 4.9",
      src: photo("1506461883276-594a12b11cf3"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Cherrapunji&source=Shillong"
    },
    {
      title: "Ziro Valley",
      subtitle: "Arunachal Pradesh · Pine Groves & Apatani Culture",
      price: "From ₹14,200 / person",
      rating: "⭐ 4.8",
      src: photo("1500534314209-a25ddb2bd429"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Ziro&source=Guwahati"
    },
    {
      title: "Coonoor",
      subtitle: "Tamil Nadu · Nilgiri Tea Gardens & Sim's Park",
      price: "From ₹7,300 / person",
      rating: "⭐ 4.7",
      src: photo("1544735716-392fe2489ffa"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Coonoor&source=Coimbatore"
    },
    {
      title: "Dandeli",
      subtitle: "Karnataka · Kali River Rafting & Canopy Walks",
      price: "From ₹6,800 / person",
      rating: "⭐ 4.7",
      src: photo("1501785888041-af3ef285b470"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Dandeli&source=Hubli"
    },
    {
      title: "Kabini",
      subtitle: "Karnataka · River Safari & Black Panther Land",
      price: "From ₹14,500 / person",
      rating: "⭐ 4.9",
      src: photo("1546182990-dffeafbe841d"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Kabini&source=Mysore"
    },
    {
      title: "Varkala",
      subtitle: "Kerala · Arabian Sea Cliffs & Sunset Beach",
      price: "From ₹8,200 / person",
      rating: "⭐ 4.8",
      src: photo("1507525428034-b723cf961d3e"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Varkala&source=Trivandrum"
    },
    {
      title: "Gulmarg",
      subtitle: "Jammu & Kashmir · Gondola & Flower Meadows",
      price: "From ₹19,000 / person",
      rating: "⭐ 4.9",
      src: photo("1486870591958-9b9d0d1dda99"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Gulmarg&source=Srinagar"
    },
    {
      title: "Almora",
      subtitle: "Uttarakhand · Kumaon Pines & Himalayan Panoramas",
      price: "From ₹7,800 / person",
      rating: "⭐ 4.7",
      src: photo("1464822759023-fed622ff2c3b"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Almora&source=Delhi"
    },
    {
      title: "Auli",
      subtitle: "Uttarakhand · Himalayan Ski Slopes & Nanda Devi",
      price: "From ₹15,400 / person",
      rating: "⭐ 4.8",
      src: photo("1519681393784-d120267933ba"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Auli&source=Rishikesh"
    },
    {
      title: "Rann of Kutch",
      subtitle: "Gujarat · Endless White Salt Desert & Rann Utsav",
      price: "From ₹11,800 / person",
      rating: "⭐ 4.8",
      src: photo("1509316975850-ff9c5deb0cd9"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Kutch&source=Bhuj"
    },
    {
      title: "Madurai",
      subtitle: "Tamil Nadu · Meenakshi Amman Temple & Heritage",
      price: "From ₹5,600 / person",
      rating: "⭐ 4.8",
      src: photo("1590050752117-238cb0fb12b1"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Madurai&source=Chennai"
    },
    {
      title: "Jodhpur",
      subtitle: "Rajasthan · The Blue City & Mehrangarh Fort",
      price: "From ₹8,900 / person",
      rating: "⭐ 4.8",
      src: photo("1524492412937-b28074a5d7da"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Jodhpur&source=Jaipur"
    },
    {
      title: "Lansdowne",
      subtitle: "Uttarakhand · Quiet Oak Forests & Garhwal Hills",
      price: "From ₹6,400 / person",
      rating: "⭐ 4.7",
      src: photo("1448375240586-882707db888b"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Lansdowne&source=Delhi"
    },
    {
      title: "Pahalgam",
      subtitle: "Jammu & Kashmir · Valley of Shepherds & Lidder",
      price: "From ₹16,500 / person",
      rating: "⭐ 4.9",
      src: photo("1506744038136-46273834b3fb"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Pahalgam&source=Srinagar"
    },
    {
      title: "Bandhavgarh",
      subtitle: "Madhya Pradesh · Royal Bengal Tiger Reserve",
      price: "From ₹15,200 / person",
      rating: "⭐ 4.8",
      src: photo("1534188753412-3e26d0d618d6"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Bandhavgarh&source=Jabalpur"
    },
    {
      title: "Kanyakumari",
      subtitle: "Tamil Nadu · Triveni Sangam & Southernmost Tip",
      price: "From ₹6,800 / person",
      rating: "⭐ 4.8",
      src: photo("1507525428034-b723cf961d3e"),
      aspect: 0.75,
      planUrl: "/planner/new?destination=Kanyakumari&source=Trivandrum"
    }
  ];
})(window);
