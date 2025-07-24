from tatami import router, get

class Health(router('/health')):
    @get
    def get_health(self):
        return 'OK'
    
class NonRouter:
    pass