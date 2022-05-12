# Scrapy spiders for Georgian websites, in one place
I created those spiders mainly for my personal projects and decided to open source them as some of them are needed just once, so instead of writing them again from start, having full list here at least as a starting point, seems the good idea for me.  

Spiders are grouped into subfolders, according to the data they collect

### list of currently added spiders
tree of folders ...



### installation
#### Warning
Code is mainly copied after few months/years of creating these spiders, so if there is some issue/problem, feel free let me know about it 


### installation
Basic installation for Python-3 projects, go to main folder and run
```python

python3 -m pip install -r requirements.txt

```


### how to run
Example of using spider called spider_name and saving data into spider_data.jl as json lines will be:
```bash
scrapy crawl spider_name -o spider_data.jl 
```
see [scrapy docs](https://docs.scrapy.org/en/latest/topics/practices.html#run-scrapy-from-a-script) for more instructions

### How to contribute

### Licence

### Todo
- [ ] add common string preprocessor/refiner functions (like removing weird characters)

### some more description

### e.t.c
