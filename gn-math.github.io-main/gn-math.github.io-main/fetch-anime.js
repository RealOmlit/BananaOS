

async function fetchAllAnime() {
  let allAnime = [];
  let page = 1;
  const perPage = 50;
  let hasNextPage = true;
  
  while (hasNextPage && page <= 40) { // 2000 anime
    const query = `
      query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
          pageInfo { hasNextPage }
          media(type: ANIME, sort: POPULARITY_DESC) {
            id
            title { romaji english native }
            type
            format
            episodes
            duration
            status
            season
            seasonYear
            averageScore
            popularity
            genres
            coverImage { large }
            startDate { year month day }
            endDate { year month day }
            nextAiringEpisode { episode airingAt }
            relations { edges { relationType node { id title { romaji } type } } }
          }
        }
      }
    `;
    
    try {
      const res = await fetch('https://graphql.anilist.co', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, variables: { page, perPage } })
      });
      const data = await res.json();
      const pageData = data.data.Page.media;
      allAnime = allAnime.concat(pageData);
      hasNextPage = data.data.Page.pageInfo.hasNextPage;
      page++;
      console.log(`Page ${page-1}: ${pageData.length} anime, total: ${allAnime.length}`);
      await new Promise(r => setTimeout(r, 100));
    } catch (e) {
      console.error('Error:', e.message);
      break;
    }
  }
  
  const fs = require('fs');
  fs.writeFileSync('anime-data.json', JSON.stringify(allAnime, null, 2));
  console.log(`Saved ${allAnime.length} anime to anime-data.json`);
}

fetchAllAnime();