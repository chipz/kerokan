from scrapy.http import Request, FormRequest
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.shell import inspect_response
import re
import json
from pprint import pprint

class MySpider(BaseSpider):
    name = 'makebase'
    allowed_domains = ['dropbox.com']
    start_urls = ['https://www.dropbox.com/login?cont=https%3A%2F%2Fwww.dropbox.com%2Fhome%2F2013']

    def parse(self, response):
        return FormRequest.from_response(response,
                    formnumber=0,
                    formdata={'login_email': 'your@email.com', 'login_password':
                        'yourpassword'},
                    callback=self.check_login_response)
    

    def check_login_response(self, response):
        """Check the response returned by a login request to see if we are
        successfully logged in.
        """
        if "Sign out" in response.body:
            self.log("Successfully logged in. Let's start crawling!")
            self.log("This is items in page %s" % response.url)

            hxs = HtmlXPathSelector(response)
            scripts = hxs.select('/html/head/script')

            if hasattr(self, 'token'):
                self.log("token exist : %s" % token)
            else:
                for script in scripts:
                    if "TOKEN" in script.extract():
                        self.root_ns = re.findall(r"root_ns: (\d+)", script.extract())[0] 
                        self.token = re.findall(r"TOKEN: '(.+?)'", script.extract())[0].decode('string_escape')

            print self.root_ns
            print self.token
            self.log("root_ns: %s" % self.root_ns)
            self.log("token: %s" % self.token)

            yield FormRequest(url = 'https://www.dropbox.com/browse/2013',
                    formdata={'Referer':'https://www.dropbox.com/login?cont=https%3A%2F%2Fwww.dropbox.com%2Fhome%2F2013',
                        'ns_id': self.root_ns,
                        't': self.token,
                        'is_xhr' : 'true'},
                    callback=self.parse_page2)
        else:
            self.log("Bad times :(")
            # Something went wrong, we couldn't log in, so nothing happens.

    def parse_page2(self, response):
        # Now the crawling can begin..
        hxs = HtmlXPathSelector(response)
        self.log("This is page %s" % response.url)

        paragraph = hxs.select('/html/body/p/text()').extract()
        dir_info = json.loads(paragraph[0])

        dir_list = {}

        for item in dir_info['file_info']:
            if(item[0] == True):
                absolute_foldername = item[3]
                local_foldername = re.findall(r".*\/(.*)", absolute_foldername)[0]
                file_url = item[8]
                dir_list[local_foldername] = file_url

                yield FormRequest(url = 'https://www.dropbox.com/browse/'+absolute_foldername,
                        formdata={'Referer':'https://www.dropbox.com/'+file_url,
                            'ns_id': self.root_ns,
                            't': self.token,
                            'is_xhr' : 'true'},
                        callback=self.parse_page2)
            elif(item[0] == False):
                absolute_foldername = item[3]
                local_foldername = re.findall(r".*\/(.*)", absolute_foldername)[0]
                file_url = item[8]
                dir_list[local_foldername] = file_url
                yield Request(file_url,
                        callback=self.save_pdf)


    def save_pdf(self, response):
        #path = self.get_path(response.url)
        filename = re.findall(r".*\/(.*)\?", response.url)[0]
        self.log("downloading file: %s" % filename)
        with open(filename, "wb") as f:
            f.write(response.body)
        self.log("done download")

