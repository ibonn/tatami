from tatami import router, get

class Health(router('/health')):
    @get
    def get_health(self):
        """Get app status"""
        return 'OK'

class NonRouter:
    def get_nothing(self):
        return 'THIS IS NOT AN ENDPOINT'
    
    def get_non_router(self):
        return 'THIS SHOULD BE AN ENDPOINT'