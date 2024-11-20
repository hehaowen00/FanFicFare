from __future__ import absolute_import
import logging
import re

from urllib.parse import urlparse

from .base_adapter import BaseSiteAdapter

logger = logging.getLogger(__name__)

def getClass():
  return NovelBinSiteAdapter

class NovelBinSiteAdapter(BaseSiteAdapter):
    @staticmethod
    def getSiteDomain():
        return "novelbin.me"

    def getSiteURLPattern(self):
        return r"https?://novelbin\.me/novel-book/(?P<story_id>.+?)(#+)*$"

    def __init__(self, configuration, url):
        super(NovelBinSiteAdapter, self).__init__(configuration, url)

        story_id = re.match(self.getSiteURLPattern(), url).group("story_id")
        self.story.setMetadata("storyId", story_id)
        self._storyId = story_id

        parsed = urlparse(url)

        baseURL = "https://novelbin.me/" + parsed.path[1:]
        self._setURL(baseURL)

    def extractChapterUrlsAndMetadata(self):
        data = self.get_request(self.url + "#tab-chapters-title")
        page = self.make_soup(data)

        element = page.find("div", attrs={"class": "books"})
        img = element.find("img", attrs={"class": "lazy"})
        self.setCoverImage(self.url, img["data-src"])

        try:
            element = page.find("div", attrs={"class": "books"})
            element = element.find("div", attrs={"class": "desc"})
            title_element = element.find("h3", attrs={"class": "title"})
            self.story.setMetadata("title", title_element.text)
        except:
            pass

        try:
            element = page.find("ul", attrs={"class": "info info-meta"})
            groups = element.find_all("li")

            for i, group in enumerate(groups):
                if "Author:" in group.text:
                    author = group.find("a")
                    self.story.addToList("authorId", author.text)
                    self.story.addToList("author", author.text)
                    break

            for i, group in enumerate(groups):
                if "Genre:" in group.text:
                    genres = group
                    for genre in genres.find_all("a"):
                        self.story.addToList("genre", genre.text)
                    break

            for i, group in enumerate(groups):
                if "Status:" in group.text:
                    status = groups[i+1]
                    if "Completed" == status.text:
                        self.story.setMetadata("status", "Completed")
                    else:
                        self.story.setMetadata("status", "In-Progress")
                    break

            element = page.find("div", attrs={"id", "tab-description"})
            description = element.find("div", attrs={"itemprop", "description"})
            summary = ""
            lines = description.text.splitlines()
            for line in lines:
                line = line.strip()
                summary = " " + line
            summary = summary.strip()
            self.setDescription(self.url, summary)
        except:
            pass

        self._extractChapters()

    def _extractChapters(self):
        chapters_url = "https://novelbin.me/ajax/chapter-archive?novelId=" + self._storyId
        data = self.get_request(chapters_url)
        page = self.make_soup(data)

        count = 0

        results = page.find_all("ul", attrs={"class": "list-chapter"})
        for group in results:
            subgroup = group.find_all("a")
            for chapter in subgroup:
                link = chapter["href"]
                if self.url not in link:
                    continue
                title = chapter["title"]
                self.add_chapter(title, link)
                count = count + 1
        self.story.setMetadata("numChapters", str(count))

    def getChapterText(self, url):
        data = self.get_request(url)
        soup = self.make_soup(data)

        content = soup.find(id="chr-content")

        chapter_header = content.find(["p", "h2", "h4", "h3"], string=re.compile(r"Chapter \d+:"))
        if chapter_header:
            chapter_header.decompose()
        
        for tags in content.find_all("script"):
            tags.decompose()

        for tags in content.find_next(["h2", "h3", "h4", "h5"]):
            tags.decompose()

        return self.utf8FromSoup(url, content)
