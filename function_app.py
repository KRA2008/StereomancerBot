import logging
import azure.functions as func
import crossPost

logger = logging.getLogger(__name__)

app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 3 * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
async def process_posts(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logger.info('The timer is past due!')
    
    logger.info('timer has triggered, beginning function')

    await crossPost.main()

    logger.info('Python timer trigger function executed.')