#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

/// Native bootstrap for the embedded Python interpreter.
@interface PyWebViewPythonRuntime : NSObject

- (BOOL)startWithEntryPoint:(NSString *)entryPoint error:(NSError * _Nullable * _Nullable)error;
- (BOOL)dispatchFunction:(NSString *)functionName
             paramsJSON:(NSString *)paramsJSON
                      id:(NSString *)valueID
                   error:(NSError * _Nullable * _Nullable)error;
- (void)stop;

@end

NS_ASSUME_NONNULL_END
