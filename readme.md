Lego updates its website at midnight Eastern time: https://www.reddit.com/r/legodeal/comments/1nz1x92/comment/nhz9xw2/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button

# What this project is
This site serves aggregated data on the price and value of Lego sets to a customizable dashboard.

## Who is this project for?
Lego purchasers who want to find the most valuable sets to buy, without having preexisting awareness of the set.

## What problem are you solving?
It is exceedingly challenging to do manual research on the value of a Lego set.  One would have to identify a candidate set, examine it on Bricklink or Brickset, then check the value of all its minifigures, or perhaps its part-out-value, then check its price history from retailers (Amazon, etc.), and ideally be aware of its sale history.

This service shows sets of interest (high part-out-value, low price-per-piece, low expected/actual discount) in a table, letting you know which sets you should consider.  Whereas before, you needed to know what sets were potentially good buys and research them further, this service puts good buys on your radar for you.

## Story
I am a Lego enthusiast who has built a respectable collection over the years.  My friends often ask me about new sets, and I find myself consistently telling them things like, "Don't buy that set; it's overpriced and will definitely go on sale for 30% within the next 3 months".  

# Design notes

1.) The scraper scripts run on scheduled GitHub Action cron jobs to keep the data current.

2.) The website shows a lot of the data for free.  This is to build goodwill with users and to establish myself in the Lego space.  This is not going to change long-term.  I want the premium users to feel rewarded, so most new features will probably be built for premium users, but low-cost, low-effort data will be available to anyone using the site.

3.) I need to build an email list to send out updated free-tier data each week or month.  Users should be able to select their desired frequency of email when they sign up.  Joining the email list should be optional; unsubscribing should be easy.