from tatami import router, get

class Health(router('/health')):
    @get
    def get_health(self):
        """Get app status"""
        return 'OK'
    
class NonRouter:
    pass